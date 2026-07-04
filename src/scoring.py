from __future__ import annotations

from collections.abc import Iterable

from .ai import AIAnalysis, analyze_event_with_openai
from .config import (
    INDUSTRY_KEYWORDS,
    PERSONA_KEYWORDS,
    SPEAKER_QUALITY_KEYWORDS,
    TARGET_INDUSTRIES,
    TARGET_PERSONAS,
)
from .models import LiveEvent, ScoredEvent


def _text_blob(event: LiveEvent) -> str:
    parts: Iterable[str] = [
        event.title,
        event.source,
        event.location,
        event.description,
        event.audience,
        " ".join(event.speakers),
        " ".join(event.tags),
    ]
    return " ".join(parts).lower()


def search_blob(event: LiveEvent) -> str:
    return _text_blob(event)


def classify_industry(event: LiveEvent) -> str:
    blob = _text_blob(event)
    best_match = "Other"
    best_score = 0
    for industry, keywords in INDUSTRY_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in blob)
        if score > best_score:
            best_match = industry
            best_score = score
    return best_match


def classify_persona(event: LiveEvent) -> str:
    blob = _text_blob(event)
    best_match = "General"
    best_score = 0
    for persona, keywords in PERSONA_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in blob)
        if score > best_score:
            best_match = persona
            best_score = score
    return best_match


def generate_questions(event: LiveEvent, industry: str, persona: str) -> list[str]:
    return [
        f"What is the biggest challenge you see in {industry.lower()} this quarter?",
        f"How are {persona.lower()}s measuring success for this topic today?",
        f"Which tactic from this session tends to produce the fastest business impact?",
    ]


def generate_followup(event: LiveEvent, persona: str) -> str:
    return (
        f"Follow up with {persona.lower()}s who asked questions about {event.title.lower()} "
        "and offer a relevant case study or practical benchmark."
    )


def score_event(event: LiveEvent) -> ScoredEvent:
    ai_analysis: AIAnalysis | None = analyze_event_with_openai(event)
    if ai_analysis is not None:
        return ScoredEvent(
            event=event,
            score=max(1, min(100, ai_analysis.score)),
            industry=ai_analysis.industry,
            persona=ai_analysis.persona,
            reason=f"AI ({ai_analysis.provider}): {ai_analysis.reason}",
            analysis_provider=ai_analysis.provider,
            suggested_questions=ai_analysis.suggested_questions or generate_questions(event, ai_analysis.industry, ai_analysis.persona),
            suggested_followup=ai_analysis.suggested_followup or generate_followup(event, ai_analysis.persona),
        )

    industry = classify_industry(event)
    persona = classify_persona(event)
    blob = _text_blob(event)

    industry_score = 35 if industry in TARGET_INDUSTRIES else 10
    persona_score = 30 if persona in TARGET_PERSONAS else 8
    speaker_score = 0
    for speaker in event.speakers:
        speaker_lower = speaker.lower()
        if any(keyword in speaker_lower for keyword in SPEAKER_QUALITY_KEYWORDS):
            speaker_score += 8
    size_score = 10 if any(token in event.expected_size for token in ["500", "200-500"]) else 5
    engagement_score = 0
    if any(keyword in blob for keyword in ["live", "workshop", "clinic", "panel", "webinar", "q&a"]):
        engagement_score = 17

    score = min(100, industry_score + persona_score + speaker_score + size_score + engagement_score)

    reasons = [
        f"Industry fit: {industry}",
        f"Persona fit: {persona}",
        f"Speaker profile and session format indicate strong business relevance",
    ]

    return ScoredEvent(
        event=event,
        score=score,
        industry=industry,
        persona=persona,
        reason="; ".join(reasons),
        analysis_provider="rule-based",
        suggested_questions=generate_questions(event, industry, persona),
        suggested_followup=generate_followup(event, persona),
    )


def score_events(events: list[LiveEvent]) -> list[ScoredEvent]:
    ranked = [score_event(event) for event in events]
    return sorted(ranked, key=lambda item: item.score, reverse=True)
