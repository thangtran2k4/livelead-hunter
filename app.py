from __future__ import annotations

import logging
import os
from datetime import date, datetime

import pandas as pd
import streamlit as st

from src.crawlers import crawl_youtube_live
from src.db import (
    DB_PATH,
    fetch_events,
    fetch_latest_scored_events,
    fetch_recent_events,
    fetch_recent_ingestion_runs,
    fetch_recent_score_history,
    get_history_counts,
    init_db,
    save_ingestion_run,
    save_scored_events,
    upsert_events,
)
from src.notifications import notify
from src.scoring import score_events, search_blob
from src.sources import get_mock_events


logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


st.set_page_config(
    page_title="Live Lead Hunter",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container { padding-top: 1.1rem; padding-bottom: 1.8rem; max-width: 1320px; }
    .stApp { background: #f5f7fb; color: #0f172a; }
    .hero {
        padding: 22px 24px;
        border-radius: 22px;
        background: linear-gradient(135deg, #ffffff 0%, #f6f9ff 100%);
        color: #0f172a;
        border: 1px solid rgba(148, 163, 184, 0.22);
        box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
    }
    .metric-box {
        background: #ffffff;
        border-radius: 16px;
        padding: 14px 16px;
        border: 1px solid rgba(148, 163, 184, 0.18);
        box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05);
        min-height: 86px;
    }
    .tiny-label { font-size: 0.78rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 0.15rem; }
    .section-title { margin-top: 0.15rem; margin-bottom: 0.4rem; }
    .panel {
        background: #ffffff;
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-radius: 18px;
        padding: 16px 16px 10px 16px;
        box-shadow: 0 8px 22px rgba(15, 23, 42, 0.05);
    }
    .muted-text { color: #64748b; }
    </style>
    """,
    unsafe_allow_html=True,
)


def _as_date(value: datetime | str) -> date:
    if isinstance(value, datetime):
        return value.date()
    return datetime.fromisoformat(value).date()


def _score_frame(scored_events):
    return pd.DataFrame(
        [
            {
                "Score": item.score,
                "Title": item.event.title,
                "Source": item.event.source,
                "Industry": item.industry,
                "Persona": item.persona,
                "Analysis": item.analysis_provider,
                "Start": item.event.start_time.strftime("%Y-%m-%d %H:%M UTC"),
                "Reason": item.reason,
            }
            for item in scored_events
        ]
    )


def _crawl_frame(rows):
    return pd.DataFrame(
        [
            {
                "Source": row["source_name"],
                "Events": row["event_count"],
                "Created": row["created_at"],
            }
            for row in rows
        ]
    )


def _recent_events_frame(rows):
    return pd.DataFrame(
        [
            {
                "Title": row["title"],
                "Source": row["source"],
                "Audience": row["audience"],
                "Start": row["start_time"],
            }
            for row in rows
        ]
    )


def _event_label(item) -> str:
    return f"{item.score:>3}  |  {item.event.title}  |  {item.event.source}  |  {item.persona}"


def _send_alert_if_enabled(scored_events, context_label: str, threshold: int, enabled: bool) -> tuple[bool, str]:
    if not enabled:
        return False, "Notifications disabled"

    hot_events = [item for item in scored_events if item.score >= threshold]
    if not hot_events:
        return False, "No events above alert threshold"

    lines = [f"{context_label}: {len(hot_events)} high-priority event(s) >= {threshold}"]
    for item in hot_events[:5]:
        lines.append(f"- {item.event.title} | {item.score} | {item.industry} | {item.persona}")

    result = notify("\n".join(lines))
    if any(result.values()):
        return True, "Alert sent"
    return False, "No notification channel configured"


init_db()

seed_events = get_mock_events()
upsert_events(seed_events)

current_events = fetch_events() or seed_events
ranked_events = fetch_latest_scored_events()
if not ranked_events:
    ranked_events = score_events(current_events)
    save_scored_events(ranked_events)

history_counts = get_history_counts()

default_search = ranked_events[0].event.title if ranked_events else "AI"

hero_left, hero_right = st.columns([3, 1], gap="large")
with hero_left:
    st.markdown(
        """
        <div class="hero">
            <div class="tiny-label">Lead generation dashboard</div>
            <h1 style="margin:0; font-size: 2.15rem;">Live Lead Hunter</h1>
            <p style="margin: 10px 0 0 0; font-size: 0.98rem; color: #475569; max-width: 760px;">
                Tìm livestream có khách hàng tiềm năng, chấm điểm nhanh, và giữ màn hình chính gọn để chỉ thấy thứ cần hành động.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with hero_right:
    st.markdown(
        """
        <div class="hero">
            <div class="tiny-label">Workflow</div>
            <div style="font-size:0.96rem; line-height:1.75; color:#334155;">
                1. Lọc theo nguồn và persona<br>
                2. Chọn livestream phù hợp<br>
                3. Mở chi tiết hoặc crawl mới
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.write("")

col1, col2, col3, col4 = st.columns(4, gap="medium")
high_score_count = len([item for item in ranked_events if item.score >= 70])
primary_sources = len({item.event.source for item in ranked_events})
top_score = ranked_events[0].score if ranked_events else 0
with col1:
    st.markdown(f'<div class="metric-box"><div class="tiny-label">Stored livestreams</div><h3 style="margin:0;">{history_counts["events"]}</h3></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="metric-box"><div class="tiny-label">Score snapshots</div><h3 style="margin:0;">{history_counts["scores"]}</h3></div>', unsafe_allow_html=True)
with col3:
    st.markdown(f'<div class="metric-box"><div class="tiny-label">High priority</div><h3 style="margin:0;">{high_score_count}</h3></div>', unsafe_allow_html=True)
with col4:
    st.markdown(f'<div class="metric-box"><div class="tiny-label">Sources covered</div><h3 style="margin:0;">{primary_sources}</h3></div>', unsafe_allow_html=True)

tab_overview, tab_crawl, tab_scoring = st.tabs(["Tổng quan", "Crawl YouTube", "Lịch sử"])

with st.sidebar:
    st.header("Bộ lọc")
    st.caption("Giữ sidebar cho thao tác, giữ màn hình chính cho kết quả.")

    st.text_input("Từ khóa", value=default_search, key="search_query", placeholder="title, description, audience, speaker...")
    st.slider("Điểm tối thiểu", 0, 100, 60, 5, key="min_score")
    st.date_input("Khoảng ngày", value=(min((_as_date(item.event.start_time) for item in ranked_events), default=date.today()), max((_as_date(item.event.start_time) for item in ranked_events), default=date.today())), key="date_range")

    st.markdown("### Nguồn và persona")
    source_options = sorted({item.event.source for item in ranked_events})
    persona_options = sorted({item.persona for item in ranked_events})
    industry_options = sorted({item.industry for item in ranked_events})
    selected_source = st.selectbox("Nguồn", ["Tất cả"] + source_options, key="selected_source") if source_options else "Tất cả"
    selected_persona = st.selectbox("Persona", ["Tất cả"] + persona_options, key="selected_persona") if persona_options else "Tất cả"
    selected_industry = st.selectbox("Ngành", ["Tất cả"] + industry_options, key="selected_industry") if industry_options else "Tất cả"

    st.markdown("### Cảnh báo")
    alert_threshold = st.slider("Alert threshold", 0, 100, 85, 5)
    enable_notifications = st.checkbox(
        "Bật cảnh báo Telegram/Slack",
        value=bool(os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID") or os.getenv("SLACK_WEBHOOK_URL")),
    )
    if st.button("Save current ranking snapshot", use_container_width=True):
        snapshot = score_events(current_events)
        save_scored_events(snapshot)
        sent, message = _send_alert_if_enabled(snapshot, "Manual snapshot", alert_threshold, enable_notifications)
        if sent:
            st.success(f"Snapshot saved to SQLite. {message}.")
        else:
            st.success("Snapshot saved to SQLite.")
            st.caption(message)

    with st.expander("System info", expanded=False):
        st.write(f"Events in memory: {len(current_events)}")
        st.write(f"Database: {DB_PATH}")
        st.write(f"Notifications: {'On' if enable_notifications else 'Off'}")
        st.write(f"Sources available: {source_options or ['-']}")

with tab_overview:
    st.subheader("Livestream phù hợp nhất")
    st.caption("Màn hình này chỉ giữ những thứ cần hành động: danh sách rút gọn và một livestream đang xem.")

    min_date = min((_as_date(item.event.start_time) for item in ranked_events), default=date.today())
    max_date = max((_as_date(item.event.start_time) for item in ranked_events), default=date.today())
    date_range = st.session_state.get("date_range", (min_date, max_date))
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = min_date, max_date

    search_text = st.session_state.get("search_query", "").strip().lower()
    min_score = st.session_state.get("min_score", 60)

    filtered_events = [
        item
        for item in ranked_events
        if (selected_source == "Tất cả" or item.event.source == selected_source)
        and (selected_industry == "Tất cả" or item.industry == selected_industry)
        and (selected_persona == "Tất cả" or item.persona == selected_persona)
        and item.score >= min_score
        and start_date <= _as_date(item.event.start_time) <= end_date
        and (not search_text or search_text in search_blob(item.event))
    ]

    top_left, top_right = st.columns([2, 1], gap="large")

    with top_left:
        if filtered_events:
            df = _score_frame(filtered_events)
            st.dataframe(
                df[["Score", "Title", "Source", "Industry", "Persona", "Analysis", "Start"]],
                use_container_width=True,
                hide_index=True,
                height=320,
            )
            st.download_button(
                "Download filtered CSV",
                data=df.to_csv(index=False).encode("utf-8"),
                file_name="filtered_livestreams.csv",
                mime="text/csv",
                use_container_width=True,
            )
        else:
            st.info("Không có livestream nào khớp bộ lọc hiện tại.")

    with top_right:
        with st.container(border=True):
            st.markdown('<div class="tiny-label">Xem chi tiết</div>', unsafe_allow_html=True)
            if filtered_events:
                labels = [_event_label(item) for item in filtered_events]
                selected_label = st.selectbox("Chọn livestream", labels, label_visibility="collapsed")
                selected_index = labels.index(selected_label)
                selected_item = filtered_events[selected_index]

                st.metric("Lead score", selected_item.score)
                st.progress(int(selected_item.score))
                st.write(f"**Title:** {selected_item.event.title}")
                st.write(f"**Source:** {selected_item.event.source}")
                st.write(f"**Time:** {selected_item.event.start_time.strftime('%d %b %Y %H:%M UTC')}")
                st.write(f"**Industry:** {selected_item.industry}")
                st.write(f"**Persona:** {selected_item.persona}")
                st.write(f"**Audience:** {selected_item.event.audience}")
                st.write(f"**Use case:** {selected_item.reason}")
                st.link_button("Open event", selected_item.event.url)

                with st.expander("Suggested questions", expanded=False):
                    for question in selected_item.suggested_questions:
                        st.write(f"- {question}")

                with st.expander("Follow-up idea", expanded=False):
                    st.write(selected_item.suggested_followup)
            else:
                st.info("Chọn lại bộ lọc để xem chi tiết livestream phù hợp.")

        with st.container(border=True):
            st.markdown('<div class="tiny-label">Top 10 scores</div>', unsafe_allow_html=True)
            if ranked_events:
                chart_data = pd.DataFrame({"Title": [item.event.title for item in ranked_events[:10]], "Score": [item.score for item in ranked_events[:10]]})
                st.bar_chart(chart_data.set_index("Title"), use_container_width=True)
            else:
                st.info("Chưa có dữ liệu xếp hạng.")

with tab_crawl:
    st.subheader("Crawl YouTube")
    st.caption("Chỉ giữ input cần thiết và kết quả crawl gần nhất.")

    crawl_col1, crawl_col2 = st.columns([2, 1], gap="large")
    with crawl_col1:
        with st.form("youtube_crawl_form"):
            query = st.text_input("Từ khóa tìm kiếm", value="AI SaaS sales webinar")
            max_results = st.slider("Số kết quả tối đa", 1, 10, 5)
            crawl_button = st.form_submit_button("Chạy crawl YouTube")

    if crawl_button:
        try:
            with st.spinner("Crawling YouTube Live..."):
                crawled_events = crawl_youtube_live(query=query, max_results=max_results)
                if crawled_events:
                    upsert_events(crawled_events)
                    save_ingestion_run("YouTube Live", len(crawled_events))
                    scored_events = score_events(crawled_events)
                    save_scored_events(scored_events)
                    sent, message = _send_alert_if_enabled(scored_events, f"YouTube crawl query='{query}'", alert_threshold, enable_notifications)
                    st.success(f"Đã lưu {len(crawled_events)} livestream từ YouTube vào SQLite.")
                    if sent:
                        st.info(message)
                    st.rerun()
                else:
                    save_ingestion_run("YouTube Live", 0)
                    st.info("Không tìm thấy livestream phù hợp với truy vấn này.")
        except Exception as exc:
            logger.exception("YouTube crawl failed")
            save_ingestion_run("YouTube Live", 0)
            st.error(f"YouTube crawl failed: {exc}")

    with crawl_col2:
        with st.container(border=True):
            st.markdown('<div class="tiny-label">Gợi ý</div>', unsafe_allow_html=True)
            st.write("Dùng query ngắn, gắn theo ngành hoặc persona. Ví dụ: `AI SaaS webinar`, `HR recruiting live`.")
            st.write("Khi có kết quả, hệ thống sẽ tự lưu vào SQLite và chấm điểm lại.")

    recent_runs = fetch_recent_ingestion_runs(limit=12)
    st.markdown("### Lịch sử crawl gần nhất")
    if recent_runs:
        crawl_df = _crawl_frame(recent_runs)
        st.dataframe(crawl_df, use_container_width=True, hide_index=True, height=240)
        st.download_button(
            "Tải CSV lịch sử crawl",
            data=crawl_df.to_csv(index=False).encode("utf-8"),
            file_name="crawl_history.csv",
            mime="text/csv",
            use_container_width=True,
        )
    else:
        st.info("Chưa có lịch sử crawl.")

    recent_events = fetch_recent_events(limit=20)
    if recent_events:
        with st.expander("Recent stored events", expanded=False):
            events_df = _recent_events_frame(recent_events)
            st.dataframe(events_df, use_container_width=True, hide_index=True, height=220)

with tab_scoring:
    st.subheader("Lịch sử scoring")
    st.caption("Chỉ giữ các cột quan trọng để đọc nhanh và tránh nhiễu.")
    score_history = fetch_recent_score_history(limit=50)
    if score_history:
        score_df = pd.DataFrame(score_history)
        st.dataframe(score_df[["title", "source", "score", "industry", "persona", "analysis_provider", "scored_at"]], use_container_width=True, hide_index=True, height=300)
        st.download_button(
            "Tải CSV lịch sử scoring",
            data=score_df.to_csv(index=False).encode("utf-8"),
            file_name="scoring_history.csv",
            mime="text/csv",
            use_container_width=True,
        )
        with st.expander("Phân bố nguồn phân tích", expanded=False):
            provider_counts = score_df["analysis_provider"].value_counts().reset_index()
            provider_counts.columns = ["Provider", "Count"]
            st.dataframe(provider_counts, use_container_width=True, hide_index=True)
    else:
        st.info("Chưa có lịch sử scoring. Hãy lưu snapshot hoặc chạy crawl YouTube.")


