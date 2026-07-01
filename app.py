from __future__ import annotations

import pandas as pd
import streamlit as st

from src.db import (
    DB_PATH,
    fetch_events,
    fetch_latest_scored_events,
    fetch_recent_ingestion_runs,
    fetch_recent_score_history,
    get_history_counts,
    init_db,
    save_ingestion_run,
    save_scored_events,
    upsert_events,
)
from src.crawlers import crawl_youtube_live
from src.scoring import score_events
from src.sources import get_mock_events


st.set_page_config(
    page_title="Live Lead Hunter",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.25rem;
        padding-bottom: 2rem;
        max-width: 1440px;
    }
    .stApp {
        background: linear-gradient(180deg, #f9fbff 0%, #eef6ff 100%);
        color: #0f172a;
    }
    .hero {
        padding: 22px 24px;
        border-radius: 24px;
        background: linear-gradient(135deg, #ffffff 0%, #f3f7ff 100%);
        color: #0f172a;
        box-shadow: 0 14px 30px rgba(15, 23, 42, 0.08);
        border: 1px solid rgba(148, 163, 184, 0.22);
    }
    .metric-box {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 18px;
        padding: 16px 18px;
        border: 1px solid rgba(148, 163, 184, 0.25);
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
        min-height: 88px;
    }
    .metric-label {
        color: #475569;
        font-size: 0.9rem;
        margin-top: 4px;
    }
    .section-title {
        margin-top: 0.25rem;
        margin-bottom: 0.5rem;
    }
    .event-card {
        background: rgba(255, 255, 255, 0.98);
        border: 1px solid rgba(148, 163, 184, 0.22);
        border-radius: 20px;
        padding: 18px 18px 8px 18px;
        box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
    }
    .muted-text {
        color: #64748b;
    }
    .tiny-label {
        font-size: 0.82rem;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 0.25rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

init_db()

seed_events = get_mock_events()
upsert_events(seed_events)

current_events = fetch_events()
if not current_events:
    current_events = seed_events

ranked_events = fetch_latest_scored_events()
if not ranked_events:
    ranked_events = score_events(current_events)
    save_scored_events(ranked_events)

history_counts = get_history_counts()

st.markdown(
    """
    <div class="hero">
        <h1 style="margin:0; font-size: 2.2rem;">Live Lead Hunter</h1>
        <p style="margin: 10px 0 0 0; font-size: 1rem; color: #475569;">
            Discover, rank, and engage livestreams where your next customers are already concentrated.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")

col1, col2, col3, col4 = st.columns(4, gap="medium")
high_score_count = len([item for item in ranked_events if item.score >= 70])
with col1:
    st.markdown(
        f'<div class="metric-box"><div class="tiny-label">Stored livestreams</div><h3 style="margin:0;">{history_counts["events"]}</h3></div>',
        unsafe_allow_html=True,
    )
with col2:
    st.markdown(
        f'<div class="metric-box"><div class="tiny-label">Score snapshots</div><h3 style="margin:0;">{history_counts["scores"]}</h3></div>',
        unsafe_allow_html=True,
    )
with col3:
    st.markdown(
        f'<div class="metric-box"><div class="tiny-label">High priority</div><h3 style="margin:0;">{high_score_count}</h3></div>',
        unsafe_allow_html=True,
    )
with col4:
    top_score = ranked_events[0].score if ranked_events else 0
    st.markdown(
        f'<div class="metric-box"><div class="tiny-label">Top lead score</div><h3 style="margin:0;">{top_score}</h3></div>',
        unsafe_allow_html=True,
    )

tab_overview, tab_crawl, tab_scoring = st.tabs(["Overview", "Lịch sử crawl", "Lịch sử scoring"])

with st.sidebar:
    st.header("Controls")
    st.caption("Lưu lịch sử vào SQLite, sau đó lọc theo nguồn và điểm.")
    if st.button("Save current ranking snapshot", use_container_width=True):
        snapshot = score_events(current_events)
        save_scored_events(snapshot)
        st.success("Snapshot saved to SQLite")

    st.divider()
    st.subheader("Data source")
    st.write(f"Events in memory: {len(current_events)}")
    st.write("Database: SQLite")

with tab_overview:
    st.subheader("Ranked events")
    sources = sorted({item.event.source for item in ranked_events})
    selected_sources = st.multiselect("Source", sources, default=sources, placeholder="Choose sources") if sources else []
    min_score = st.slider("Minimum score", 0, 100, 60, 5)
    industry_options = ["All"] + sorted({item.industry for item in ranked_events}) if ranked_events else ["All"]
    selected_industry = st.selectbox("Industry", industry_options)

    filtered_events = [
        item
        for item in ranked_events
        if item.event.source in selected_sources
        and item.score >= min_score
        and (selected_industry == "All" or item.industry == selected_industry)
    ]

    left_panel, right_panel = st.columns([1.7, 1], gap="large")

    with left_panel:
        if filtered_events:
            df = pd.DataFrame(
                [
                    {
                        "Score": item.score,
                        "Title": item.event.title,
                        "Source": item.event.source,
                        "Industry": item.industry,
                        "Persona": item.persona,
                        "Start": item.event.start_time.strftime("%Y-%m-%d %H:%M UTC"),
                    }
                    for item in filtered_events
                ]
            )
            st.dataframe(df, use_container_width=True, hide_index=True)

            for item in filtered_events:
                with st.container(border=True):
                    st.markdown(f"### {item.event.title}")
                    st.caption(f"{item.event.source} · {item.event.start_time.strftime('%d %b %Y %H:%M UTC')}")
                    top_row = st.columns([1, 1, 1])
                    with top_row[0]:
                        st.metric("Lead score", item.score)
                    with top_row[1]:
                        st.write(f"**Industry:** {item.industry}")
                    with top_row[2]:
                        st.write(f"**Persona:** {item.persona}")

                    c1, c2 = st.columns([2, 1])
                    with c1:
                        st.write(f"**Audience:** {item.event.audience}")
                        st.write(f"**Why it fits:** {item.reason}")
                        st.link_button("Open event", item.event.url)
                    with c2:
                        st.write("**Suggested questions**")
                        for question in item.suggested_questions:
                            st.write(f"- {question}")

                    st.write("**Suggested follow-up**")
                    st.write(item.suggested_followup)
        else:
            st.info("No events match the current filters. Try lowering the score threshold.")

    with right_panel:
        st.markdown('<h3 class="section-title">Opportunity mix</h3>', unsafe_allow_html=True)
        if ranked_events:
            chart_data = pd.DataFrame(
                {
                    "Title": [item.event.title for item in ranked_events],
                    "Score": [item.score for item in ranked_events],
                }
            )
            st.bar_chart(chart_data.set_index("Title"), use_container_width=True)
        else:
            st.info("No ranked events available yet.")

        st.markdown('<h3 class="section-title">SQLite status</h3>', unsafe_allow_html=True)
        st.caption(f"Database file: {DB_PATH}")
        st.write(f"Events stored: {history_counts['events']}")
        st.write(f"Score rows: {history_counts['scores']}")
        st.write(f"Ingestion runs: {history_counts['runs']}")

with tab_crawl:
    st.subheader("YouTube Live crawl")
    st.caption("Crawl từ nguồn công khai bằng yt-dlp search; hiện ưu tiên YouTube Live trước.")

    with st.form("youtube_crawl_form"):
        query = st.text_input("Search query", value="AI SaaS sales webinar")
        max_results = st.slider("Max results", 1, 10, 5)
        crawl_button = st.form_submit_button("Run YouTube crawl")

    if crawl_button:
        try:
            with st.spinner("Crawling YouTube Live..."):
                crawled_events = crawl_youtube_live(query=query, max_results=max_results)
                if crawled_events:
                    upsert_events(crawled_events)
                    save_ingestion_run("YouTube Live", len(crawled_events))
                    scored_events = score_events(crawled_events)
                    save_scored_events(scored_events)
                    st.success(f"Crawled {len(crawled_events)} YouTube live event(s) and saved to SQLite.")
                    st.rerun()
                else:
                    save_ingestion_run("YouTube Live", 0)
                    st.info("No live/upcoming YouTube results matched this query.")
        except Exception as exc:
            save_ingestion_run("YouTube Live", 0)
            st.error(f"YouTube crawl failed: {exc}")

    crawl_runs = fetch_recent_ingestion_runs(limit=20)
    if crawl_runs:
        st.markdown("### Recent crawl runs")
        st.dataframe(pd.DataFrame(crawl_runs), use_container_width=True, hide_index=True)
    else:
        st.info("No crawl history yet. Run a YouTube crawl to store the first run.")

    youtubes = [item for item in fetch_events() if item.source == "YouTube Live"]
    if youtubes:
        st.markdown("### Crawled YouTube events")
        yt_df = pd.DataFrame(
            [
                {
                    "Title": item.title,
                    "Start": item.start_time.strftime("%Y-%m-%d %H:%M UTC"),
                    "Audience": item.audience,
                    "URL": item.url,
                }
                for item in youtubes[-10:]
            ]
        )
        st.dataframe(yt_df, use_container_width=True, hide_index=True)

with tab_scoring:
    st.subheader("Scoring history")
    st.caption("Mỗi lần crawl hoặc bấm lưu snapshot đều tạo lịch sử scoring trong SQLite.")
    score_history = fetch_recent_score_history(limit=50)
    if score_history:
        score_df = pd.DataFrame(score_history)
        st.dataframe(score_df, use_container_width=True, hide_index=True)
    else:
        st.info("Chưa có lịch sử scoring. Hãy lưu snapshot hoặc chạy crawl YouTube.")


