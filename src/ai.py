from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from typing import Any

import requests

from .models import LiveEvent


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AIAnalysis:
    industry: str
    persona: str
    score: int
    reason: str
    promotional_comment: str
    suggested_questions: list[str]
    suggested_followup: str
    provider: str


def _build_prompt(event: LiveEvent) -> str:
    return (
        "You are a B2B sales strategist. Analyze the livestream/event and return JSON only with keys: "
        "industry, persona, score, reason, promotional_comment, suggested_questions, suggested_followup. "
        "Score must be an integer from 1 to 100. Keep suggested_questions as a list of 3 short questions. "
        "The promotional_comment should be a short, engaging sentence in Vietnamese introducing that you represent company ABC offering service CD ('tôi đại diện doanh nghiệp ABC cung cấp dịch vụ CD') and how it can help the viewers. "
        "Focus on lead-generation value, audience fit, and conversation quality.\n\n"
        f"Title: {event.title}\n"
        f"Source: {event.source}\n"
        f"Description: {event.description}\n"
        f"Audience: {event.audience}\n"
        f"Speakers: {', '.join(event.speakers)}\n"
        f"Tags: {', '.join(event.tags)}\n"
    )


def analyze_event_with_openai(event: LiveEvent) -> AIAnalysis | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Return strict JSON only."},
            {"role": "user", "content": _build_prompt(event)},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }

    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        body = response.json()
        content = body["choices"][0]["message"]["content"]
        data = json.loads(content)
        return AIAnalysis(
            industry=str(data.get("industry", "Other")),
            persona=str(data.get("persona", "General")),
            score=int(data.get("score", 50)),
            reason=str(data.get("reason", "AI analysis completed.")),
            promotional_comment=str(data.get("promotional_comment", "")),
            suggested_questions=[str(item) for item in data.get("suggested_questions", [])][:3],
            suggested_followup=str(data.get("suggested_followup", "")),
            provider=f"openai:{model}",
        )
    except Exception as exc:
        logger.warning("OpenAI analysis failed, falling back to rules", exc_info=True)
        return None


def analysis_as_dict(analysis: AIAnalysis) -> dict[str, Any]:
    return asdict(analysis)
