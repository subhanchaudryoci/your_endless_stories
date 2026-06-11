from __future__ import annotations

import ast
import json
import os
from dataclasses import asdict
from typing import Any, Callable, Optional

from models.schemas import ChildProfile, StoryBook, VocabularyItem
from services import prompts


class GenAIError(RuntimeError):
    """Raised when OCI Generative AI cannot complete a request."""


_LAST_ERROR: Optional[str] = None


def last_genai_error() -> Optional[str]:
    return _LAST_ERROR


def _set_last_error(message: Optional[str]) -> None:
    global _LAST_ERROR
    _LAST_ERROR = message


def demo_mode_enabled() -> bool:
    return os.getenv("YES_DEMO_MODE", "").strip().lower() in {"1", "true", "yes", "on"}


def genai_status() -> dict[str, Any]:
    missing = []
    if not os.getenv("OCI_GENAI_MODEL_ID"):
        missing.append("OCI_GENAI_MODEL_ID")
    if not os.getenv("OCI_COMPARTMENT_ID"):
        missing.append("OCI_COMPARTMENT_ID")

    region_available = bool(os.getenv("OCI_REGION") or os.getenv("OCI_GENAI_ENDPOINT"))
    config_file = os.getenv("OCI_CONFIG_FILE") or os.path.expanduser("~/.oci/config")
    if not region_available and not os.path.exists(config_file):
        missing.append("OCI_REGION or OCI config file")

    configured = not missing and not demo_mode_enabled()
    return {
        "configured": configured,
        "demo_mode": demo_mode_enabled() or bool(missing),
        "missing": missing,
    }


def call_oci_genai(
    prompt: str,
    *,
    system_prompt: Optional[str] = None,
    temperature: float = 0.4,
    max_tokens: int = 2400,
) -> str:
    """Single wrapper for every OCI Generative AI call in the app."""
    status = genai_status()
    if not status["configured"]:
        raise GenAIError(f"OCI Generative AI is not configured. Missing: {', '.join(status['missing'])}")

    try:
        import oci
        from oci.generative_ai_inference import GenerativeAiInferenceClient
        from oci.generative_ai_inference import models
    except ImportError as exc:
        raise GenAIError("The oci package is not installed. Run pip install -r requirements.txt.") from exc

    try:
        model_id = os.environ["OCI_GENAI_MODEL_ID"]
        compartment_id = os.environ["OCI_COMPARTMENT_ID"]
        config_file = os.getenv("OCI_CONFIG_FILE", os.path.expanduser("~/.oci/config"))
        config_profile = os.getenv("OCI_CONFIG_PROFILE", "DEFAULT")
        auth_mode = os.getenv("OCI_AUTH", "api_key").strip().lower()

        signer = None
        if auth_mode == "resource_principal":
            signer = oci.auth.signers.get_resource_principals_signer()
            config = {"region": os.getenv("OCI_REGION", "")}
        elif auth_mode == "instance_principal":
            signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
            config = {"region": os.getenv("OCI_REGION", "")}
        else:
            config = oci.config.from_file(config_file, config_profile)

        region = os.getenv("OCI_REGION") or config.get("region")
        endpoint = os.getenv("OCI_GENAI_ENDPOINT") or f"https://inference.generativeai.{region}.oci.oraclecloud.com"
        client_kwargs = {
            "config": config,
            "service_endpoint": endpoint,
            "timeout": (10, 240),
            "retry_strategy": oci.retry.DEFAULT_RETRY_STRATEGY,
        }
        if signer is not None:
            client_kwargs["signer"] = signer
        client = GenerativeAiInferenceClient(**client_kwargs)

        full_prompt = prompt if not system_prompt else f"{system_prompt}\n\n{prompt}"
        chat_request = _build_chat_request(models, model_id, full_prompt, temperature, max_tokens)
        chat_details = models.ChatDetails(
            compartment_id=compartment_id,
            serving_mode=models.OnDemandServingMode(model_id=model_id),
            chat_request=chat_request,
        )

        response = client.chat(chat_details)
    except Exception as exc:
        raise GenAIError(f"OCI Generative AI request failed: {exc}") from exc

    text = _extract_response_text(response.data)
    if not text:
        raise GenAIError("OCI Generative AI returned an empty response.")
    return text


def _build_chat_request(models: Any, model_id: str, prompt: str, temperature: float, max_tokens: int) -> Any:
    if model_id.startswith("cohere.") and hasattr(models, "CohereChatRequestV2"):
        return models.CohereChatRequestV2(
            api_format=models.CohereChatRequestV2.API_FORMAT_COHEREV2,
            messages=[
                models.CohereUserMessageV2(
                    role="USER",
                    content=[models.CohereTextContentV2(type="TEXT", text=prompt)],
                )
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            is_stream=False,
        )

    try:
        return models.GenericChatRequest(
            api_format=models.GenericChatRequest.API_FORMAT_GENERIC,
            messages=[
                models.UserMessage(
                    role="USER",
                    content=[models.TextContent(type="TEXT", text=prompt)],
                )
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            is_stream=False,
        )
    except AttributeError:
        request = models.CohereChatRequest()
        request.message = prompt
        request.temperature = temperature
        request.max_tokens = max_tokens
        request.is_stream = False
        return request


def _extract_response_text(data: Any) -> str:
    chat_response = getattr(data, "chat_response", None)
    if chat_response is None:
        return ""

    choices = getattr(chat_response, "choices", None)
    if choices:
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", None)
        if isinstance(content, list) and content:
            return str(getattr(content[0], "text", "")).strip()
        if isinstance(content, str):
            return content.strip()

    message = getattr(chat_response, "message", None)
    if message is not None:
        content = getattr(message, "content", None)
        if isinstance(content, list) and content:
            texts = [str(getattr(item, "text", "")).strip() for item in content]
            return "\n".join(text for text in texts if text).strip()
        if isinstance(content, str):
            return content.strip()

    for attr in ("text", "message", "content"):
        value = getattr(chat_response, attr, None)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def parse_json_payload(raw: str) -> Optional[Any]:
    text = raw.strip()
    if text.startswith("```"):
        lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()

    for candidate in _json_candidates(text):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            try:
                parsed = ast.literal_eval(candidate)
                if isinstance(parsed, (dict, list)):
                    return parsed
            except (SyntaxError, ValueError):
                continue
    return None


def _json_candidates(text: str) -> list[str]:
    candidates = [text]
    object_start = text.find("{")
    object_end = text.rfind("}")
    if object_start != -1 and object_end != -1 and object_end > object_start:
        candidates.append(text[object_start : object_end + 1])
    array_start = text.find("[")
    array_end = text.rfind("]")
    if array_start != -1 and array_end != -1 and array_end > array_start:
        candidates.append(text[array_start : array_end + 1])
    return candidates


def _request_json(
    task_name: str,
    prompt: str,
    fallback_factory: Callable[[], dict[str, Any]],
    *,
    temperature: float = 0.4,
    max_tokens: int = 2400,
) -> tuple[dict[str, Any], str]:
    if not genai_status()["configured"]:
        _set_last_error(None)
        return fallback_factory(), "demo"

    try:
        _set_last_error(None)
        raw = call_oci_genai(
            prompt,
            system_prompt=prompts.SAFETY_SYSTEM_PROMPT,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        parsed = parse_json_payload(raw)
        if isinstance(parsed, dict):
            return parsed, "oci"

        strict_prompt = (
            f"The previous {task_name} response was not valid JSON. "
            "Return only one valid JSON object, with double quoted keys and strings. "
            "Do not include markdown, commentary, or code fences.\n\n"
            f"{prompt}"
        )
        raw = call_oci_genai(
            strict_prompt,
            system_prompt=prompts.SAFETY_SYSTEM_PROMPT,
            temperature=0.2,
            max_tokens=max_tokens,
        )
        parsed = parse_json_payload(raw)
        if isinstance(parsed, dict):
            return parsed, "oci"
    except GenAIError as exc:
        _set_last_error(str(exc))

    return fallback_factory(), "fallback"


def generate_storybook(profile: ChildProfile, theme_hint: str = "") -> StoryBook:
    story_data, story_source = _request_json(
        "story generation",
        prompts.story_prompt(profile, theme_hint),
        lambda: _demo_story(profile, theme_hint),
        temperature=0.55,
    )
    story_data = _sanitize_story_data(story_data, profile, theme_hint)

    vocabulary_words = [item.get("word", "") for item in story_data.get("vocabulary", []) if isinstance(item, dict)]
    question_data, question_source = _request_json(
        "question generation",
        prompts.question_prompt(profile, story_data["title"], story_data["story_text"], vocabulary_words),
        lambda: {"questions": _demo_questions(story_data["title"], vocabulary_words)},
        temperature=0.35,
    )
    story_data["questions"] = _sanitize_questions(question_data.get("questions"), story_data["title"], vocabulary_words)

    hint_words = story_data.get("tricky_words") or vocabulary_words
    hint_data, hint_source = _request_json(
        "hint generation",
        prompts.hint_prompt(profile, story_data["story_text"], hint_words),
        lambda: {"hints": _demo_hints(hint_words)},
        temperature=0.25,
        max_tokens=1200,
    )
    _merge_hints(story_data, hint_data.get("hints", []))

    sources = {story_source, question_source, hint_source}
    if sources == {"oci"}:
        source = "oci"
    elif sources == {"demo"}:
        source = "demo"
    else:
        source = "fallback"
    return StoryBook.from_dict(story_data, child_id=profile.id or 0, source=source)


def generate_parent_summary(profile: ChildProfile, sessions: list[Any]) -> dict[str, Any]:
    compact_sessions = []
    for session in sessions[:6]:
        compact_sessions.append(
            {
                "date": session.created_at[:10],
                "total_score": session.total_score,
                "comprehension_points": session.score.comprehension,
                "phonics_points": session.score.phonics_decoding,
                "fluency_points": session.score.fluency,
                "independence_points": session.score.independence,
                "consistency_points": session.score.consistency,
                "strengths": session.score.strengths,
                "weak_areas": session.score.weak_areas,
            }
        )

    summary, _source = _request_json(
        "parent summary generation",
        prompts.parent_summary_prompt(profile, compact_sessions),
        lambda: _demo_parent_summary(profile, compact_sessions),
        temperature=0.3,
        max_tokens=1000,
    )
    return _sanitize_parent_summary(summary)


def _sanitize_story_data(data: dict[str, Any], profile: ChildProfile, theme_hint: str) -> dict[str, Any]:
    if not data.get("title") or not data.get("story_text"):
        data = _demo_story(profile, theme_hint)

    vocabulary = data.get("vocabulary")
    if not isinstance(vocabulary, list) or len(vocabulary) < 3:
        vocabulary = _demo_story(profile, theme_hint)["vocabulary"]
    data["vocabulary"] = [
        asdict(VocabularyItem.from_dict(item))
        for item in vocabulary
        if isinstance(item, dict) and str(item.get("word", "")).strip()
    ][:8]

    tricky_words = data.get("tricky_words")
    if not isinstance(tricky_words, list) or not tricky_words:
        tricky_words = [item["word"] for item in data["vocabulary"]]
    data["tricky_words"] = [str(word).strip() for word in tricky_words if str(word).strip()][:10]
    data["theme"] = str(data.get("theme") or theme_hint or ", ".join(profile.interests[:2]) or "reading adventure")
    return data


def _sanitize_questions(raw_questions: Any, title: str, vocabulary_words: list[str]) -> list[dict[str, Any]]:
    if not isinstance(raw_questions, list):
        return _demo_questions(title, vocabulary_words)

    questions: list[dict[str, Any]] = []
    allowed_types = {"literal", "sequence", "vocabulary", "inference"}
    for item in raw_questions:
        if not isinstance(item, dict):
            continue
        options = item.get("options")
        answer = str(item.get("answer", "")).strip()
        if not isinstance(options, list) or len(options) < 2 or answer not in options:
            continue
        qtype = str(item.get("question_type", "literal")).strip().lower()
        if qtype not in allowed_types:
            qtype = "literal"
        questions.append(
            {
                "question_type": qtype,
                "question": str(item.get("question", "")).strip(),
                "options": [str(option).strip() for option in options[:4]],
                "answer": answer,
                "explanation": str(item.get("explanation", "")).strip(),
            }
        )

    if len(questions) < 3:
        return _demo_questions(title, vocabulary_words)
    return questions[:5]


def _merge_hints(story_data: dict[str, Any], hints: Any) -> None:
    if not isinstance(hints, list):
        hints = []
    hint_map = {
        str(item.get("word", "")).strip().lower(): item
        for item in hints
        if isinstance(item, dict) and item.get("word")
    }
    for item in story_data.get("vocabulary", []):
        key = item["word"].lower()
        if key in hint_map:
            item["hint"] = str(hint_map[key].get("hint") or item.get("hint") or "")
            item["pattern"] = str(hint_map[key].get("pattern") or item.get("pattern") or "")


def _demo_story(profile: ChildProfile, theme_hint: str = "") -> dict[str, Any]:
    name = profile.name.strip() or "Sam"
    interest = theme_hint.strip() or (profile.interests[0] if profile.interests else "maps")
    second_interest = profile.interests[1] if len(profile.interests) > 1 else "stars"
    if profile.age <= 6:
        story_text = (
            f"{name} found a tiny map beside a red lunch box. The map had a path to a quiet {interest} garden. "
            f"{name} said, \"I can try one step at a time.\" On the path, a robin chirped, chip-chip-chip. "
            f"The sound helped {name} tap each word: map, path, garden. At the gate, a sign said, \"Read to open.\" "
            f"{name} read the words slowly. The gate swung wide. Inside, bright leaves made shapes like {second_interest}. "
            f"{name} picked three seed cards and read each clue. First, water the small seed. Next, hum a soft tune. "
            f"Last, wait and watch. A sprout popped up and made a new sign: \"Good readers try again.\" "
            f"{name} smiled and read the sign two more times."
        )
    else:
        story_text = (
            f"{name} joined the neighborhood reading club with a notebook, a pencil, and a question about {interest}. "
            f"The club's first challenge was to follow clues through a small discovery trail. The first clue was hidden "
            f"under a bench: \"Look for the place where shadows point north.\" {name} paused, reread the sentence, and "
            f"noticed the tallest tree leaning over the path. Near its roots was a box covered with stickers of {second_interest}. "
            f"Inside the box, a card explained that careful readers collect evidence before they guess. The next clue used "
            f"a new word, observe. {name} sounded it out in chunks: ob-serve. Then {name} looked closely at the trail and "
            f"found three blue stones in a row. At the end, the club leader asked how the clues connected. {name} answered, "
            f"\"Each clue asked me to slow down, notice details, and use proof from the text.\" The leader nodded and handed "
            f"{name} a bookmark that said, \"Strong readers think while they read.\""
        )

    return {
        "title": f"{name}'s Reading Trail",
        "theme": interest,
        "story_text": story_text,
        "vocabulary": [
            {"word": "trail", "meaning": "a path to follow", "hint": "Starts with the tr blend: tr-ail", "pattern": "tr blend"},
            {"word": "clue", "meaning": "a hint that helps solve something", "hint": "The ue says oo", "pattern": "ue vowel team"},
            {"word": "observe", "meaning": "to look closely", "hint": "Break it into ob-serve", "pattern": "syllables"},
            {"word": "evidence", "meaning": "details that show what is true", "hint": "Say ev-i-dence in three parts", "pattern": "syllables"},
            {"word": "careful", "meaning": "taking time to do something well", "hint": "Care plus ful", "pattern": "suffix -ful"},
        ],
        "tricky_words": ["trail", "clue", "observe", "evidence", "careful"],
    }


def _demo_questions(title: str, vocabulary_words: list[str]) -> list[dict[str, Any]]:
    vocab_word = vocabulary_words[0] if vocabulary_words else "trail"
    return [
        {
            "question_type": "literal",
            "question": f"What did the main character follow in {title}?",
            "options": ["A set of clues", "A loud drum", "A shopping list"],
            "answer": "A set of clues",
            "explanation": "The story is about following clues on a reading trail.",
        },
        {
            "question_type": "sequence",
            "question": "What happened before the character answered the final question?",
            "options": ["The character collected evidence", "The character went to sleep", "The character lost the notebook"],
            "answer": "The character collected evidence",
            "explanation": "The character used details from the clues before answering.",
        },
        {
            "question_type": "vocabulary",
            "question": f"What does the word '{vocab_word}' mean in the story?",
            "options": ["A path to follow", "A kind of dessert", "A very loud sound"],
            "answer": "A path to follow",
            "explanation": "A trail is a path.",
        },
        {
            "question_type": "inference",
            "question": "Why did the character reread the clue?",
            "options": ["To understand it better", "To make the clue disappear", "To skip the challenge"],
            "answer": "To understand it better",
            "explanation": "Rereading helped the character notice important details.",
        },
    ]


def _demo_hints(words: list[str]) -> list[dict[str, str]]:
    pattern_by_word = {
        "trail": ("Say tr first, then ail like sail.", "tr blend, ai vowel team"),
        "clue": ("The ue team sounds like oo.", "ue vowel team"),
        "observe": ("Break it into ob-serve.", "two syllables"),
        "evidence": ("Tap ev-i-dence in three beats.", "three syllables"),
        "careful": ("Read care, then add ful.", "base word plus suffix"),
    }
    hints = []
    for word in words:
        hint, pattern = pattern_by_word.get(str(word).lower(), (f"Break {word} into smaller sound chunks.", "chunking"))
        hints.append({"word": str(word), "hint": hint, "pattern": pattern})
    return hints


def _demo_parent_summary(profile: ChildProfile, sessions: list[dict[str, Any]]) -> dict[str, Any]:
    if not sessions:
        return {
            "summary": f"{profile.name} has a profile ready but no completed reading sessions yet.",
            "strengths": ["Ready to begin"],
            "weak_areas": ["No session data yet"],
            "next_practice": "Generate a short story and complete the first quiz.",
        }
    latest = sessions[0]
    return {
        "summary": (
            f"{profile.name}'s latest session score was {latest['total_score']:.0f}/100. "
            "The recent pattern suggests short, focused practice is working best."
        ),
        "strengths": latest.get("strengths", ["Participation"]),
        "weak_areas": latest.get("weak_areas", ["No major weak area"]),
        "next_practice": "Review the tricky words, then reread one paragraph before the next quiz.",
    }


def _sanitize_parent_summary(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "summary": str(summary.get("summary", "")).strip() or "No summary available yet.",
        "strengths": [str(item).strip() for item in summary.get("strengths", []) if str(item).strip()] or ["No sessions yet"],
        "weak_areas": [str(item).strip() for item in summary.get("weak_areas", []) if str(item).strip()] or ["No major weak area"],
        "next_practice": str(summary.get("next_practice", "")).strip() or "Complete another short reading session.",
    }
