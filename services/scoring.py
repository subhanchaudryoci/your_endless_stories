from __future__ import annotations

import re
from typing import Any

from models.schemas import ChildProfile, QuizQuestion, ReadingSession, ScoreBreakdown


WEIGHTS = {
    "comprehension": 40,
    "phonics_decoding": 20,
    "fluency": 15,
    "independence": 15,
    "consistency": 10,
}


def _normalize_answer(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9 ]+", "", value)
    return re.sub(r"\s+", " ", value)


def is_correct_answer(selected: str, expected: str) -> bool:
    return _normalize_answer(selected) == _normalize_answer(expected)


def _consistency_points(profile: ChildProfile, prior_sessions: list[ReadingSession], current_base_points: float) -> float:
    current_scaled = (current_base_points / 90) * 100
    if prior_sessions:
        recent = prior_sessions[:3]
        reference = sum(session.total_score for session in recent) / len(recent)
    elif profile.baseline_score is not None:
        reference = profile.baseline_score
    else:
        return 7.0

    delta = current_scaled - reference
    if delta >= 0:
        return 10.0
    if delta >= -5:
        return 8.0
    if delta >= -10:
        return 6.0
    return 4.0


def _area_percent(points: float, weight: int) -> float:
    return round((points / weight) * 100, 1) if weight else 0


def _points_from_percent(percent: float, weight: int) -> float:
    return round((max(0.0, min(100.0, percent)) / 100) * weight, 1)


def _question_percent(question_results: list[dict[str, Any]], question_types: set[str], fallback_percent: float) -> float:
    matches = [
        result
        for result in question_results
        if str(result.get("type", "")).strip().lower().replace(" ", "_") in question_types
    ]
    if not matches:
        return fallback_percent
    correct = sum(1 for result in matches if result["correct"])
    return round((correct / len(matches)) * 100, 1)


def _is_answered(value: str) -> bool:
    normalized = _normalize_answer(value)
    return bool(normalized) and normalized not in {"choose an answer", "i am not sure", "not sure"}


def _recommendation(weak_areas: list[str], strengths: list[str]) -> str:
    if "Comprehension" in weak_areas:
        return "Practice retelling the beginning, middle, and end before answering questions."
    if "Phonics and decoding" in weak_areas:
        return "Spend five minutes blending the tricky words aloud before the next story."
    if "Fluency" in weak_areas:
        return "Reread one short paragraph twice, aiming for smooth phrasing."
    if "Independence" in weak_areas:
        return "Let the child try each question first, then offer one hint if needed."
    if "Consistency" in weak_areas:
        return "Keep sessions short and regular, then compare the next score to today's result."
    if strengths:
        return f"Build on {strengths[0].lower()} with a slightly richer vocabulary list next time."
    return "Continue with short, interest-led stories and one focused reread."


def calculate_session_score(
    profile: ChildProfile,
    questions: list[QuizQuestion],
    answers: dict[str, str],
    prior_sessions: list[ReadingSession],
) -> tuple[ScoreBreakdown, float]:
    question_results: list[dict[str, Any]] = []
    correct_count = 0

    for index, question in enumerate(questions):
        selected = answers.get(str(index), "")
        correct = is_correct_answer(selected, question.answer)
        if correct:
            correct_count += 1
        question_results.append(
            {
                "index": index,
                "type": question.question_type,
                "question": question.question,
                "selected": selected,
                "answer": question.answer,
                "correct": correct,
                "explanation": question.explanation,
            }
        )

    quiz_percent = round((correct_count / len(questions)) * 100, 1) if questions else 0.0
    comprehension = _points_from_percent(quiz_percent, WEIGHTS["comprehension"])

    phonics_percent = _question_percent(
        question_results,
        {"vocabulary", "phonics", "phonics_decoding", "decoding"},
        quiz_percent,
    )
    fluency_percent = _question_percent(
        question_results,
        {"literal", "sequence", "sequencing"},
        quiz_percent,
    )
    answered_count = sum(1 for result in question_results if _is_answered(str(result.get("selected", ""))))
    unsure_count = sum(1 for result in question_results if "not sure" in _normalize_answer(str(result.get("selected", ""))))
    question_count = len(questions)
    completion_percent = round((answered_count / question_count) * 100, 1) if question_count else 0.0
    unsure_penalty = round((unsure_count / question_count) * 20, 1) if question_count else 0.0
    independence_percent = max(0.0, min(100.0, (completion_percent * 0.6) + (quiz_percent * 0.4) - unsure_penalty))

    phonics_decoding = _points_from_percent(phonics_percent, WEIGHTS["phonics_decoding"])
    fluency = _points_from_percent(fluency_percent, WEIGHTS["fluency"])
    independence = _points_from_percent(independence_percent, WEIGHTS["independence"])

    base_points = comprehension + phonics_decoding + fluency + independence
    consistency = _consistency_points(profile, prior_sessions, base_points)
    total = round(base_points + consistency, 1)

    area_scores = {
        "Comprehension": _area_percent(comprehension, WEIGHTS["comprehension"]),
        "Phonics and decoding": _area_percent(phonics_decoding, WEIGHTS["phonics_decoding"]),
        "Fluency": _area_percent(fluency, WEIGHTS["fluency"]),
        "Independence": _area_percent(independence, WEIGHTS["independence"]),
        "Consistency": _area_percent(consistency, WEIGHTS["consistency"]),
    }
    strengths = [area for area, percent in area_scores.items() if percent >= 80]
    weak_areas = [area for area, percent in area_scores.items() if percent < 70]
    if not strengths:
        strengths = ["Steady participation"]
    if not weak_areas:
        weak_areas = ["No major weak area"]

    score = ScoreBreakdown(
        phonics_decoding=phonics_decoding,
        fluency=fluency,
        comprehension=comprehension,
        independence=independence,
        consistency=consistency,
        total=total,
        strengths=strengths,
        weak_areas=weak_areas,
        recommendation=_recommendation(weak_areas, strengths),
        details={
            "weights": WEIGHTS,
            "quiz_percent": quiz_percent,
            "correct_count": correct_count,
            "question_count": len(questions),
            "question_results": question_results,
            "inference_model": {
                "phonics_decoding": "Vocabulary and phonics question correctness, falling back to overall quiz accuracy.",
                "fluency": "Literal and sequence question correctness as a proxy for smooth reading and order tracking.",
                "independence": "Answer completion, quiz accuracy, and reduced not-sure responses.",
                "consistency": "Comparison with recent sessions or baseline score.",
            },
            "inferred_percents": {
                "phonics_decoding": phonics_percent,
                "fluency": fluency_percent,
                "independence": round(independence_percent, 1),
                "completion": completion_percent,
                "not_sure_count": unsure_count,
            },
            "area_percents": area_scores,
        },
    )
    return score, quiz_percent


def aggregate_strengths_and_needs(sessions: list[ReadingSession]) -> dict[str, list[str]]:
    strengths: dict[str, int] = {}
    needs: dict[str, int] = {}
    for session in sessions:
        for area in session.score.strengths:
            strengths[area] = strengths.get(area, 0) + 1
        for area in session.score.weak_areas:
            if area != "No major weak area":
                needs[area] = needs.get(area, 0) + 1

    ranked_strengths = [item for item, _ in sorted(strengths.items(), key=lambda pair: pair[1], reverse=True)]
    ranked_needs = [item for item, _ in sorted(needs.items(), key=lambda pair: pair[1], reverse=True)]
    return {
        "strengths": ranked_strengths or ["No sessions yet"],
        "weak_areas": ranked_needs or ["No major weak area"],
    }
