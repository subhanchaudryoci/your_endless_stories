from __future__ import annotations

from models.schemas import ChildProfile


SAFETY_SYSTEM_PROMPT = """You create child-safe reading practice for a local Streamlit app.
Keep content warm, non-scary, non-violent, age-appropriate, and educational.
Avoid unsafe instructions, mature themes, stereotypes, medical/legal advice, and collecting personal data.
Use simple language matched to the child's age. Return only valid JSON for JSON tasks."""


def reading_band(age: int) -> str:
    if age <= 5:
        return "emergent reader: short sentences, common CVC words, repetition, gentle phonics"
    if age <= 7:
        return "early reader: simple paragraphs, decodable words, clear sequence, concrete vocabulary"
    if age <= 9:
        return "developing reader: short chapters, richer vocabulary, cause and effect, basic inference"
    return "confident reader: concise literary prose, more varied vocabulary, inference, theme, and context clues"


def profile_context(profile: ChildProfile) -> str:
    interests = ", ".join(profile.interests) if profile.interests else "general adventure"
    baseline = "not provided" if profile.baseline_score is None else f"{profile.baseline_score:.0f}/100"
    return (
        f"Child nickname: {profile.name}\n"
        f"Age: {profile.age}\n"
        f"Reading band: {reading_band(profile.age)}\n"
        f"Interests: {interests}\n"
        f"Reading goal: {profile.reading_goal}\n"
        f"Baseline score: {baseline}"
    )


def story_prompt(profile: ChildProfile, theme_hint: str = "") -> str:
    theme_line = f"\nPreferred theme for this story: {theme_hint}" if theme_hint else ""
    return f"""Create a short personalized storybook for reading practice.

{profile_context(profile)}{theme_line}

Return JSON with this exact shape:
{{
  "title": "string",
  "theme": "string",
  "story_text": "string, 180 to 450 words depending on age, no markdown",
  "vocabulary": [
    {{"word": "string", "meaning": "simple child-friendly definition", "hint": "pronunciation or decoding hint", "pattern": "phonics pattern"}}
  ],
  "tricky_words": ["string"]
}}

Rules:
- Use the child's interests naturally without revealing private information.
- Keep the story demo-friendly and complete.
- Include 5 to 8 vocabulary words.
- Include decodable tricky words or phonics patterns appropriate for the age.
- Do not include quiz questions in this response."""


def question_prompt(profile: ChildProfile, title: str, story_text: str, vocabulary_words: list[str]) -> str:
    vocab = ", ".join(vocabulary_words[:8])
    return f"""Create a quiz for this child after reading the story.

{profile_context(profile)}

Story title: {title}
Vocabulary words: {vocab}
Story:
{story_text}

Return JSON with this exact shape:
{{
  "questions": [
    {{
      "question_type": "literal | sequence | vocabulary | inference",
      "question": "string",
      "options": ["string", "string", "string"],
      "answer": "one exact option string",
      "explanation": "one short sentence"
    }}
  ]
}}

Rules:
- Create exactly 4 questions.
- Include at least one literal, one sequence, one vocabulary, and one inference question.
- Every answer must exactly match one option.
- Keep wording age-appropriate and unambiguous."""


def hint_prompt(profile: ChildProfile, story_text: str, words: list[str]) -> str:
    words_text = ", ".join(words[:10])
    return f"""Create reading help for selected tricky words.

{profile_context(profile)}

Story:
{story_text}

Words: {words_text}

Return JSON with this exact shape:
{{
  "hints": [
    {{"word": "string", "hint": "simple decoding hint", "pattern": "phonics pattern"}}
  ]
}}

Rules:
- Keep hints short and child-friendly.
- Focus on sound chunks, syllables, blends, vowel teams, or context clues.
- Return one hint per word."""


def parent_summary_prompt(profile: ChildProfile, sessions: list[dict]) -> str:
    return f"""Create a short parent progress summary.

{profile_context(profile)}

Recent sessions:
{sessions}

Return JSON with this exact shape:
{{
  "summary": "2 to 3 sentences",
  "strengths": ["string"],
  "weak_areas": ["string"],
  "next_practice": "one practical recommendation"
}}

Rules:
- Be specific and encouraging without exaggerating.
- Do not diagnose learning disabilities.
- Base the recommendation only on the provided scores."""

