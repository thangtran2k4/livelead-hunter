from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from src.ai import AIAnalysis
from src.models import LiveEvent
from src.scoring import score_event


class ScoringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.event = LiveEvent(
            title="AI Sales Automation Webinar",
            source="YouTube Live",
            url="https://example.com/live",
            start_time=datetime(2026, 7, 10, 10, 0, tzinfo=timezone.utc),
            timezone="UTC",
            location="Online",
            description="A live session about AI sales automation for SaaS founders and revenue teams.",
            speakers=["Jane Doe, Founder"],
            expected_size="200-500",
            audience="Founders, Sales Leaders",
            tags=["AI", "Sales", "SaaS"],
        )

    @patch("src.scoring.analyze_event_with_openai", return_value=None)
    def test_rule_based_fallback(self, _mock_ai: object) -> None:
        scored = score_event(self.event)
        self.assertEqual(scored.analysis_provider, "rule-based")
        self.assertGreaterEqual(scored.score, 1)
        self.assertTrue(scored.suggested_questions)

    @patch("src.scoring.analyze_event_with_openai")
    def test_ai_analysis_is_used_when_available(self, mock_ai: object) -> None:
        mock_ai.return_value = AIAnalysis(
            industry="AI",
            persona="Founder",
            score=93,
            reason="Strong founder-led AI SaaS audience.",
            suggested_questions=["What problem are you solving first?", "How do you qualify the best leads?"],
            suggested_followup="Offer a short benchmark and ask for a follow-up call.",
            provider="openai:gpt-4o-mini",
        )
        scored = score_event(self.event)
        self.assertEqual(scored.analysis_provider, "openai:gpt-4o-mini")
        self.assertEqual(scored.score, 93)
        self.assertEqual(scored.industry, "AI")
        self.assertEqual(scored.persona, "Founder")


if __name__ == "__main__":
    unittest.main()
