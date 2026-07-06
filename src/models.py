from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List


@dataclass(frozen=True)
class LiveEvent:
    title: str
    source: str
    url: str
    start_time: datetime
    timezone: str
    location: str
    description: str
    speakers: List[str] = field(default_factory=list)
    expected_size: str = "Unknown"
    audience: str = "Unknown"
    tags: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ScoredEvent:
    event: LiveEvent
    score: int
    industry: str
    persona: str
    reason: str
    promotional_comment: str = ""
    analysis_provider: str = "rule-based"
    suggested_questions: List[str] = field(default_factory=list)
    suggested_followup: str = ""
