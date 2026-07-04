from __future__ import annotations

import logging
from datetime import datetime, timezone
from urllib.parse import quote_plus

from yt_dlp import YoutubeDL

from ..models import LiveEvent


logger = logging.getLogger(__name__)


def _to_datetime(timestamp: object | None) -> datetime:
    if isinstance(timestamp, (int, float)):
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)
    return datetime.now(timezone.utc)


def _build_event(info: dict[str, object]) -> LiveEvent:
    title = str(info.get("title") or info.get("fulltitle") or "Untitled YouTube live")
    url = str(info.get("webpage_url") or info.get("original_url") or "")
    description = str(info.get("description") or "")
    uploader = str(info.get("uploader") or info.get("channel") or "YouTube creator")
    live_status = str(info.get("live_status") or "").lower()
    audience = "Live viewers" if live_status == "is_live" else "Potential attendees"
    tags = [tag for tag in [str(info.get("channel") or ""), str(info.get("categories") or "")] if tag]
    release_timestamp = info.get("release_timestamp") or info.get("timestamp")

    return LiveEvent(
        title=title,
        source="YouTube Live",
        url=url,
        start_time=_to_datetime(release_timestamp),
        timezone="UTC",
        location="Online",
        description=description or f"YouTube live result from {uploader}",
        speakers=[uploader],
        expected_size="Unknown",
        audience=audience,
        tags=tags,
    )


def crawl_youtube_live(query: str, max_results: int = 10) -> list[LiveEvent]:
    search_opts = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": True,
        "noplaylist": True,
        "ignoreerrors": True,
        "playlistend": max_results,
    }

    events: list[LiveEvent] = []
    search_terms = f"https://www.youtube.com/results?search_query={query}&sp=EgJAAQ%253D%253D"
    with YoutubeDL(search_opts) as ydl:
        search_result = ydl.extract_info(search_terms, download=False)

    entries = (search_result or {}).get("entries") or []
    if not entries:
        fallback_query = quote_plus(query)
        fallback_url = f"https://www.youtube.com/results?search_query={fallback_query}"
        with YoutubeDL(search_opts) as ydl:
            search_result = ydl.extract_info(fallback_url, download=False)
        entries = (search_result or {}).get("entries") or []

    logger.info("YouTube crawl search completed", extra={"query": query, "max_results": max_results})

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        video_id = entry.get("id")
        if not video_id:
            continue
        video_url = str(entry.get("url") or f"https://www.youtube.com/watch?v={video_id}")

        detail_opts = {
            "quiet": True,
            "skip_download": True,
            "ignoreerrors": True,
        }
        with YoutubeDL(detail_opts) as ydl:
            detail = ydl.extract_info(video_url, download=False)

        if not isinstance(detail, dict):
            continue

        live_status = str(detail.get("live_status") or "").lower()
        if live_status not in {"is_live", "is_upcoming"}:
            continue

        events.append(_build_event(detail))

    return events