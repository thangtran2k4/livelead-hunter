from __future__ import annotations

import csv
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Generator
import re

from .models import LiveEvent, ScoredEvent


DB_PATH = Path(__file__).resolve().parents[1] / "data" / "live_leads.sqlite3"


def _ensure_parent_directory() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def connect() -> Generator[sqlite3.Connection, None, None]:
    _ensure_parent_directory()
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def init_db() -> None:
    with connect() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS live_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                external_id TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                start_time TEXT NOT NULL,
                timezone TEXT NOT NULL,
                location TEXT NOT NULL,
                description TEXT NOT NULL,
                speakers_json TEXT NOT NULL,
                expected_size TEXT NOT NULL,
                audience TEXT NOT NULL,
                tags_json TEXT NOT NULL,
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS event_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                score INTEGER NOT NULL,
                industry TEXT NOT NULL,
                persona TEXT NOT NULL,
                reason TEXT NOT NULL,
                suggested_questions_json TEXT NOT NULL,
                suggested_followup TEXT NOT NULL,
                analysis_provider TEXT NOT NULL DEFAULT 'rule-based',
                scored_at TEXT NOT NULL,
                FOREIGN KEY(event_id) REFERENCES live_events(id)
            );

            CREATE TABLE IF NOT EXISTS ingestion_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_name TEXT NOT NULL,
                event_count INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )

        columns = connection.execute("PRAGMA table_info(event_scores)").fetchall()
        column_names = {row["name"] for row in columns}
        if "analysis_provider" not in column_names:
            connection.execute("ALTER TABLE event_scores ADD COLUMN analysis_provider TEXT NOT NULL DEFAULT 'rule-based'")


def _external_id(event: LiveEvent) -> str:
    return f"{event.source}:{event.url}"


def upsert_events(events: list[LiveEvent]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with connect() as connection:
        for event in events:
            connection.execute(
                """
                INSERT INTO live_events (
                    source, external_id, title, url, start_time, timezone, location,
                    description, speakers_json, expected_size, audience, tags_json,
                    first_seen_at, last_seen_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(external_id) DO UPDATE SET
                    title=excluded.title,
                    url=excluded.url,
                    start_time=excluded.start_time,
                    timezone=excluded.timezone,
                    location=excluded.location,
                    description=excluded.description,
                    speakers_json=excluded.speakers_json,
                    expected_size=excluded.expected_size,
                    audience=excluded.audience,
                    tags_json=excluded.tags_json,
                    last_seen_at=excluded.last_seen_at
                """,
                (
                    event.source,
                    _external_id(event),
                    event.title,
                    event.url,
                    event.start_time.isoformat(),
                    event.timezone,
                    event.location,
                    event.description,
                    json.dumps(event.speakers, ensure_ascii=False),
                    event.expected_size,
                    event.audience,
                    json.dumps(event.tags, ensure_ascii=False),
                    now,
                    now,
                ),
            )


def fetch_events() -> list[LiveEvent]:
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT source, title, url, start_time, timezone, location, description,
                   speakers_json, expected_size, audience, tags_json
            FROM live_events
            ORDER BY start_time ASC
            """
        ).fetchall()

    events: list[LiveEvent] = []
    for row in rows:
        events.append(
            LiveEvent(
                title=row["title"],
                source=row["source"],
                url=row["url"],
                start_time=datetime.fromisoformat(row["start_time"]),
                timezone=row["timezone"],
                location=row["location"],
                description=row["description"],
                speakers=json.loads(row["speakers_json"]),
                expected_size=row["expected_size"],
                audience=row["audience"],
                tags=json.loads(row["tags_json"]),
            )
        )
    return events


def save_scored_events(scored_events: list[ScoredEvent]) -> None:
    with connect() as connection:
        for item in scored_events:
            event_row = connection.execute(
                "SELECT id FROM live_events WHERE external_id = ?",
                (_external_id(item.event),),
            ).fetchone()
            if event_row is None:
                continue
            connection.execute(
                """
                INSERT INTO event_scores (
                    event_id, score, industry, persona, reason,
                    suggested_questions_json, suggested_followup, analysis_provider, scored_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_row["id"],
                    item.score,
                    item.industry,
                    item.persona,
                    item.reason,
                    json.dumps(item.suggested_questions, ensure_ascii=False),
                    item.suggested_followup,
                    item.analysis_provider,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )


def fetch_latest_scored_events() -> list[ScoredEvent]:
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT
                e.source,
                e.title,
                e.url,
                e.start_time,
                e.timezone,
                e.location,
                e.description,
                e.speakers_json,
                e.expected_size,
                e.audience,
                e.tags_json,
                s.score,
                s.industry,
                s.persona,
                s.reason,
                s.suggested_questions_json,
                s.suggested_followup,
                s.analysis_provider
            FROM event_scores s
            JOIN live_events e ON e.id = s.event_id
            WHERE s.id IN (
                SELECT MAX(id)
                FROM event_scores
                GROUP BY event_id
            )
            ORDER BY s.score DESC, e.start_time ASC
            """
        ).fetchall()

    scored_events: list[ScoredEvent] = []
    for row in rows:
        event = LiveEvent(
            title=row["title"],
            source=row["source"],
            url=row["url"],
            start_time=datetime.fromisoformat(row["start_time"]),
            timezone=row["timezone"],
            location=row["location"],
            description=row["description"],
            speakers=json.loads(row["speakers_json"]),
            expected_size=row["expected_size"],
            audience=row["audience"],
            tags=json.loads(row["tags_json"]),
        )
        scored_events.append(
            ScoredEvent(
                event=event,
                score=row["score"],
                industry=row["industry"],
                persona=row["persona"],
                reason=row["reason"],
                analysis_provider=row["analysis_provider"],
                suggested_questions=json.loads(row["suggested_questions_json"]),
                suggested_followup=row["suggested_followup"],
            )
        )
    return scored_events


def get_history_counts() -> dict[str, int]:
    with connect() as connection:
        event_count = connection.execute("SELECT COUNT(*) AS count FROM live_events").fetchone()["count"]
        score_count = connection.execute("SELECT COUNT(*) AS count FROM event_scores").fetchone()["count"]
        run_count = connection.execute("SELECT COUNT(*) AS count FROM ingestion_runs").fetchone()["count"]
    return {
        "events": event_count,
        "scores": score_count,
        "runs": run_count,
    }


def save_ingestion_run(source_name: str, event_count: int) -> None:
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO ingestion_runs (source_name, event_count, created_at)
            VALUES (?, ?, ?)
            """,
            (source_name, event_count, datetime.now(timezone.utc).isoformat()),
        )


def fetch_recent_ingestion_runs(limit: int = 20) -> list[dict[str, object]]:
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT source_name, event_count, created_at
            FROM ingestion_runs
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def fetch_recent_score_history(limit: int = 25) -> list[dict[str, object]]:
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT
                e.title,
                e.source,
                e.description,
                s.score,
                s.industry,
                s.persona,
                s.scored_at,
                s.analysis_provider,
                s.reason
            FROM event_scores s
            JOIN live_events e ON e.id = s.event_id
            ORDER BY s.scored_at DESC, s.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def fetch_recent_events(limit: int = 50) -> list[dict[str, object]]:
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT title, source, url, start_time, location, description, expected_size, audience
            FROM live_events
            ORDER BY last_seen_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def _clean_seed_description(description: str) -> str:
    lines = [line.strip() for line in description.splitlines()]
    cleaned_lines: list[str] = []
    skip_markers = (
        "watch more",
        "follow ",
        "facebook:",
        "twitter:",
        "instagram:",
        "website:",
        "get more",
        "subscribe",
        "join this channel",
        "support the channel",
        "thanks for watching",
        "watch more interesting videos",
        "visit our website",
    )
    url_pattern = re.compile(r"https?://|www\.|bit\.ly|youtu\.be|t\.me|instagram\.com|facebook\.com|twitter\.com", re.IGNORECASE)

    for line in lines:
        if not line:
            continue
        lower_line = line.lower()
        if any(marker in lower_line for marker in skip_markers):
            continue
        if url_pattern.search(line):
            continue
        cleaned_lines.append(line)

    cleaned_text = "\n".join(cleaned_lines).strip()
    cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)
    return cleaned_text


def export_seed_events(limit: int = 50) -> str:
    events = fetch_recent_events(limit=limit)
    output = StringIO()
    fieldnames = ["title", "source", "url", "start_time", "location", "audience", "expected_size", "description"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in events:
        writer.writerow(
            {
                "title": row.get("title", ""),
                "source": row.get("source", ""),
                "url": row.get("url", ""),
                "start_time": row.get("start_time", ""),
                "location": row.get("location", ""),
                "audience": row.get("audience", ""),
                "expected_size": row.get("expected_size", ""),
                "description": _clean_seed_description(str(row.get("description", ""))),
            }
        )
    return output.getvalue()
