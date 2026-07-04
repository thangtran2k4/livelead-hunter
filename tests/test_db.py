from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from src.models import LiveEvent
from src.scoring import score_event


class DatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.sqlite3"

        self.patcher = patch("src.db.DB_PATH", self.db_path)
        self.patcher.start()

        import src.db as db

        self.db = db
        self.db.init_db()

    def tearDown(self) -> None:
        self.patcher.stop()
        self.temp_dir.cleanup()

    def test_round_trip_event_and_score(self) -> None:
        event = LiveEvent(
            title="Founder Growth Clinic",
            source="YouTube Live",
            url="https://example.com/founder-growth",
            start_time=datetime(2026, 7, 11, 9, 0, tzinfo=timezone.utc),
            timezone="UTC",
            location="Online",
            description="Clinic for founders on startup growth and revenue.",
            speakers=["Alex Kim, Founder"],
            expected_size="100-200",
            audience="Founders",
            tags=["Startup", "Growth"],
        )

        self.db.upsert_events([event])
        self.db.save_scored_events([score_event(event)])

        events = self.db.fetch_events()
        scored_events = self.db.fetch_latest_scored_events()
        counts = self.db.get_history_counts()

        self.assertEqual(len(events), 1)
        self.assertEqual(len(scored_events), 1)
        self.assertEqual(scored_events[0].analysis_provider, "rule-based")
        self.assertEqual(counts["events"], 1)
        self.assertEqual(counts["scores"], 1)


if __name__ == "__main__":
    unittest.main()
