import io
import os
import logging
from datetime import datetime

import pandas as pd
import streamlit as st

from src.crawlers import crawl_youtube_live
from src.scoring import score_events

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
    /* Dark mode, Glassmorphism, Premium feel */
    .stApp {
        background-color: #0B1120;
        color: #F8FAFC;
    }
    .block-container {
        padding-top: 2rem;
        max-width: 1300px;
    }
    .hero {
        background: rgba(30, 41, 59, 0.4);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(56, 189, 248, 0.15);
        border-radius: 24px;
        padding: 40px 30px;
        text-align: center;
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.3);
        margin-bottom: 20px;
    }
    h1 {
        font-weight: 800;
        background: linear-gradient(to right, #38BDF8, #818CF8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 10px;
    }
    h2, h3 {
        color: #E2E8F0;
    }
    .subtitle {
        color: #94A3B8;
        font-size: 1.1rem;
        max-width: 600px;
        margin: 0 auto;
        line-height: 1.6;
    }
    .metric-badge {
        display: inline-flex;
        align-items: center;
        padding: 4px 12px;
        background: rgba(14, 165, 233, 0.15);
        color: #38BDF8;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.85rem;
        margin-bottom: 15px;
        border: 1px solid rgba(14, 165, 233, 0.3);
    }
    .card {
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid rgba(148, 163, 184, 0.1);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.2);
        transition: all 0.3s ease;
    }
    .card:hover {
        transform: translateY(-4px);
        border-color: rgba(56, 189, 248, 0.4);
        box-shadow: 0 12px 30px rgba(56, 189, 248, 0.15);
    }
    .score-high {
        color: #10B981;
        font-weight: bold;
    }
    .score-med {
        color: #F59E0B;
        font-weight: bold;
    }
    .score-low {
        color: #EF4444;
        font-weight: bold;
    }
    .label {
        font-size: 0.8rem;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 4px;
    }
    .value {
        font-size: 1rem;
        color: #F1F5F9;
        margin-bottom: 16px;
    }
    .card-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #FFFFFF;
        margin-bottom: 12px;
        line-height: 1.4;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def _to_excel_bytes(scored_events) -> bytes:
    df = pd.DataFrame(
        [
            {
                "Tên live": item.event.title,
                "Nguồn": item.event.source,
                "Lĩnh vực": item.industry,
                "URL": item.event.url,
                "Ngày diễn ra": item.event.start_time.strftime("%Y-%m-%d %H:%M UTC"),
                "Nội dung": item.event.description,
                "Comment": item.promotional_comment,
            }
            for item in scored_events
        ]
    )
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Livestreams")
    return output.getvalue()


with st.sidebar:
    st.markdown("## 🎯 Quét Livestream")
    st.caption("Tìm và phân tích trực tiếp theo thời gian thực.")
    st.write("---")
    
    with st.form("search_form"):
        query = st.text_input("Từ khóa", value="AI SaaS sales", placeholder="Nhập từ khóa...")
        max_results = st.slider("Số kết quả tối đa", 1, 20, 5)
        st.write("")
        submit = st.form_submit_button("Crawl & Score Hiện Tại", use_container_width=True)

if submit:
    st.session_state["scored_events"] = []
    
    with st.spinner(f"Đang crawl dữ liệu YouTube cho '{query}'..."):
        try:
            raw_events = crawl_youtube_live(query=query, max_results=max_results)
        except Exception as exc:
            logger.exception("Crawl failed")
            st.error(f"Lỗi khi crawl: {exc}")
            raw_events = []
            
    if raw_events:
        with st.spinner("Đang gọi AI chấm điểm & tạo comment..."):
            scored = score_events(raw_events)
            st.session_state["scored_events"] = scored
    elif "scored_events" not in st.session_state or not st.session_state["scored_events"]:
        st.warning("Không tìm thấy livestream nào đang diễn ra với từ khóa này.")

if "scored_events" in st.session_state and st.session_state["scored_events"]:
    events = st.session_state["scored_events"]
    
    # Header Section
    col_title, col_export = st.columns([3, 1], gap="large")
    with col_title:
        st.markdown(f"### 🚀 Tìm thấy **{len(events)}** livestream tiềm năng")
    with col_export:
        excel_data = _to_excel_bytes(events)
        st.download_button(
            label="📥 Tải Excel Report",
            data=excel_data,
            file_name=f"live_leads_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary"
        )
    st.write("---")
    
    # Display Results in a dynamic grid
    for i, item in enumerate(events):
        score_class = "score-high" if item.score >= 70 else "score-med" if item.score >= 40 else "score-low"
        
        # HTML for custom Card
        card_html = f"""<div class="card">
<div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 15px;">
<div class="metric-badge">Điểm AI: <span style="margin-left:5px" class="{score_class}">{item.score}</span></div>
<div style="font-size: 0.8rem; color: #94A3B8;">{item.event.source} | {item.analysis_provider}</div>
</div>
<div class="card-title">{item.event.title}</div>
<div style="display: flex; gap: 30px; margin-top: 15px; margin-bottom: 15px;">
<div>
<div class="label">Ngành (Industry)</div>
<div class="value">{item.industry}</div>
</div>
<div>
<div class="label">Chân dung (Persona)</div>
<div class="value">{item.persona}</div>
</div>
<div>
<div class="label">Quy mô</div>
<div class="value">{item.event.expected_size}</div>
</div>
</div>
<div class="label">Lý do chọn (AI Analysis)</div>
<div class="value" style="font-size: 0.9rem; line-height: 1.5; color: #CBD5E1;">{item.reason}</div>
</div>"""
        st.markdown(card_html, unsafe_allow_html=True)
        
        # Streamlit interactive components inside the card
        col_link, col_exp = st.columns([1, 4])
        with col_link:
            st.link_button("Mở Livestream", item.event.url, use_container_width=True)
        with col_exp:
            with st.expander("💬 Promotional Comment & Ideas", expanded=False):
                st.code(item.promotional_comment, language="text")
                st.markdown("**Câu hỏi gợi ý tương tác:**")
                for q in item.suggested_questions:
                    st.markdown(f"- {q}")
        st.write("") # spacing
        
else:
    # Empty State Hero
    st.markdown(
        """
        <div class="hero">
            <div class="metric-badge">Stateless & Real-time</div>
            <h1>Live Lead Hunter</h1>
            <p class="subtitle">
                Hệ thống tìm kiếm livestream thông minh không lưu trữ DB. <br/>
                Sử dụng menu bên trái để bắt đầu quét các luồng trực tiếp mới nhất trên YouTube và dùng AI để tạo comment quảng bá.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
