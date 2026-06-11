from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_interests(value: str | list[str]) -> list[str]:
    if isinstance(value, list):
        return [item.strip() for item in value if str(item).strip()]
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass
class ChildProfile:
    id: Optional[int]
    name: str
    age: int
    interests: list[str]
    reading_goal: str
    baseline_score: Optional[float] = None
    created_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VocabularyItem:
    word: str
    meaning: str
    hint: str
    pattern: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VocabularyItem":
        return cls(
            word=str(data.get("word", "")).strip(),
            meaning=str(data.get("meaning", "")).strip(),
            hint=str(data.get("hint", "")).strip(),
            pattern=str(data.get("pattern", "")).strip(),
        )


@dataclass
class QuizQuestion:
    question: str
    question_type: str
    options: list[str]
    answer: str
    explanation: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QuizQuestion":
        options = data.get("options") or []
        if not isinstance(options, list):
            options = []
        return cls(
            question=str(data.get("question", "")).strip(),
            question_type=str(data.get("question_type", data.get("type", "literal"))).strip(),
            options=[str(option).strip() for option in options if str(option).strip()],
            answer=str(data.get("answer", "")).strip(),
            explanation=str(data.get("explanation", "")).strip(),
        )


@dataclass
class StoryBook:
    id: Optional[int]
    child_id: int
    title: str
    story_text: str
    vocabulary: list[VocabularyItem]
    questions: list[QuizQuestion]
    tricky_words: list[str]
    theme: str = ""
    source: str = "demo"
    created_at: str = field(default_factory=utc_now_iso)

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        child_id: int,
        source: str = "oci",
        story_id: Optional[int] = None,
    ) -> "StoryBook":
        vocabulary = [VocabularyItem.from_dict(item) for item in data.get("vocabulary", []) if isinstance(item, dict)]
        questions = [QuizQuestion.from_dict(item) for item in data.get("questions", []) if isinstance(item, dict)]
        tricky_words = data.get("tricky_words") or [item.word for item in vocabulary]
        return cls(
            id=story_id,
            child_id=child_id,
            title=str(data.get("title", "A New Reading Adventure")).strip(),
            story_text=str(data.get("story_text", "")).strip(),
            vocabulary=vocabulary,
            questions=questions,
            tricky_words=[str(word).strip() for word in tricky_words if str(word).strip()],
            theme=str(data.get("theme", "")).strip(),
            source=source,
            created_at=str(data.get("created_at") or utc_now_iso()),
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["vocabulary"] = [asdict(item) for item in self.vocabulary]
        data["questions"] = [asdict(item) for item in self.questions]
        return data


@dataclass
class ScoreBreakdown:
    phonics_decoding: float
    fluency: float
    comprehension: float
    independence: float
    consistency: float
    total: float
    strengths: list[str]
    weak_areas: list[str]
    recommendation: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReadingSession:
    id: Optional[int]
    child_id: int
    story_id: int
    answers: dict[str, str]
    score: ScoreBreakdown
    quiz_score: float
    total_score: float
    notes: str = ""
    created_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

