import requests
import streamlit as st
import os
from datetime import datetime
from st_copy_to_clipboard import st_copy_to_clipboard
from streamlit_autorefresh import st_autorefresh

# =========================================================
# CONFIG
# =========================================================
API_URL = os.getenv("API_URL", "http://localhost:8000")
PAGE_SIZE = 20
REQUEST_TIMEOUT = 10

# =========================================================
# PAGE SETUP
# =========================================================
st.set_page_config(
    page_title="BoltLink | Analytics",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# True background polling — fires a rerun every 10s regardless of user interaction
st_autorefresh(interval=10_000, key="engagement_refresh")

# =========================================================
# PREMIUM GLASSMORPHISM STYLING
# =========================================================
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus+Jakarta+Sans', sans-serif;
    }

    .main {
        background: radial-gradient(circle at 50% 0%, #1e293b 0%, #0f172a 100%);
        color: #f8fafc;
    }

    /* Hero Section */
    .hero-container {
        text-align: center;
        padding: 3rem 0;
        background: linear-gradient(180deg, rgba(56, 189, 248, 0.05) 0%, transparent 100%);
        border-radius: 0 0 50px 50px;
        margin-bottom: 2rem;
    }

    .hero-title {
        font-size: 3.5rem;
        font-weight: 800;
        background: linear-gradient(90deg, #fff 0%, #38bdf8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }

    /* Modern Link Cards */
    .link-card {
        background: rgba(30, 41, 59, 0.4);
        border: 1px solid rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(12px);
        border-radius: 24px;
        padding: 1.5rem;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        margin-bottom: 1rem;
    }

    .link-card:hover {
        transform: translateY(-5px);
        background: rgba(30, 41, 59, 0.6);
        border-color: rgba(56, 189, 248, 0.4);
        box-shadow: 0 20px 40px -20px rgba(0, 0, 0, 0.5);
    }

    /* Glass Metrics */
    [data-testid="metric-container"] {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        backdrop-filter: blur(8px);
        padding: 1.5rem !important;
        border-radius: 20px !important;
    }

    /* Status Badge */
    .status-pill {
        padding: 4px 12px;
        border-radius: 50px;
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        background: rgba(56, 189, 248, 0.1);
        color: #38bdf8;
        border: 1px solid rgba(56, 189, 248, 0.2);
    }

    /* Primary Action Button */
    .stButton > button {
        border-radius: 14px !important;
        background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%) !important;
        border: none !important;
        font-weight: 600 !important;
        padding: 0.6rem 2rem !important;
        transition: 0.3s ease !important;
    }

    .stButton > button:hover {
        transform: scale(1.02);
        box-shadow: 0 0 20px rgba(14, 165, 233, 0.4) !important;
    }

    .st-copy-to-clipboard-btn {
        display: flex !important;
        width: 100% !important;
        justify-content: center;
    }
</style>
""",
    unsafe_allow_html=True,
)


# =========================================================
# APP LOGIC & API (Abstracted)
# =========================================================
class APIClient:
    @staticmethod
    def shorten(url: str):
        return requests.post(f"{API_URL}/shorten", json={"target_url": url}).json()

    @staticmethod
    def fetch(page: int, limit: int):
        return requests.get(
            f"{API_URL}/links", params={"page": page, "limit": limit}
        ).json()

    @staticmethod
    def delete(link_id: str):
        requests.delete(f"{API_URL}/links/{link_id}").raise_for_status()

    @staticmethod
    def fetch_summary(short_id: str) -> str | None:
        try:
            res = requests.get(f"{API_URL}/links/{short_id}/summary", timeout=10)
            res.raise_for_status()
            data = res.json()
            return data.get("summary")
        except Exception:
            return None

    @staticmethod
    def fetch_stats() -> dict:
        try:
            res = requests.get(f"{API_URL}/stats", timeout=5)
            res.raise_for_status()
            return res.json()
        except Exception:
            return {"total_links": 0, "total_clicks": 0}


# =========================================================
# UTILITIES
# =========================================================


def format_date(date_str: str) -> str:
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y")
    except Exception:
        return date_str


def change_page(page: int):
    st.session_state.page = page


# =========================================================
# HEADER
# =========================================================

st.markdown(
    """
<div class="hero-container">
    <div class="hero-title">⚡ BoltLink</div>
    <div class="hero-subtitle">
        Enterprise-grade URL shortening & analytics
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# 1. Input Section
with st.container():
    col_in, col_btn = st.columns([4, 1])
    with col_in:
        url_input = st.text_input(
            "Destination URL",
            placeholder="https://your-very-long-destination-url.com",
            label_visibility="collapsed",
        )
    with col_btn:
        if st.button("Create Link", use_container_width=True):
            if url_input:
                res = APIClient.shorten(url_input)
                st.balloons()
                st.success(f"Short URL: {res['short_url']}")

# 2. Metrics — live stats from /stats endpoint
if "page" not in st.session_state:
    st.session_state.page = 1

stats = APIClient.fetch_stats()
payload = APIClient.fetch(st.session_state.page, PAGE_SIZE)
items, total = payload.get("items", []), payload.get("total", 0)

m1, m2, m3 = st.columns(3)
m1.metric("Global Links", stats["total_links"])
m2.metric("Total Engagement", stats["total_clicks"])
m3.metric("Current Page", st.session_state.page)

# 3. Managed Links
st.markdown("### 📊 Active Distributions")

if not items:
    st.info("No links found.")
else:
    for link in items:
        # Data Setup
        sid = link.get("short_id", link.get("id"))
        link_id = link.get("id")
        clicks = link.get("clicks", 0)
        target = link.get("original_url", "No URL")
        created = format_date(link.get("created_at", ""))

        with st.container():
            # IMPORTANT: Keep the HTML flush left inside the f-string
            st.markdown(
                f"""
<div class="link-card">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div style="overflow: hidden; flex: 1;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.5rem; font-weight: 800; color: #38bdf8;">/{sid}</span>
                <span class="status-pill">Active</span>
            </div>
            <div style="color: #94a3b8; font-size: 0.85rem; font-family: monospace; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-top: 5px;">
                {target}
            </div>
        </div>
        <div style="text-align: right; min-width: 120px; margin-left: 20px;">
            <div style="font-size: 1.6rem; font-weight: 800; color: white;">{clicks}</div>
            <div style="font-size: 0.65rem; color: #475569; text-transform: uppercase; letter-spacing: 1px;">Total Clicks</div>
            <div style="font-size: 0.7rem; color: #64748b; margin-top: 4px;">{created}</div>
        </div>
    </div>
</div>
""",
                unsafe_allow_html=True,
            )

            # Native Buttons - These should be indented normally
            btn_col1, btn_col2, btn_col3, btn_col4, _ = st.columns([1, 1, 1, 1, 3])
            with btn_col1:
                st.link_button("🌐 Open", f"{API_URL}/{sid}", use_container_width=True)
            with btn_col2:
                st_copy_to_clipboard(
                    f"{API_URL}/{sid}",
                    before_copy_label="📋 Copy",
                    after_copy_label="✅ Copied",
                )

            with btn_col3:
                with st.popover("🤖 AI Summary", use_container_width=True):
                    summary_key = f"summary_{link_id}"
                    if summary_key not in st.session_state:
                        st.session_state[summary_key] = None

                    if st.button(
                        "Generate Summary",
                        key=f"gen_summary_{link_id}",
                        use_container_width=True,
                    ):
                        with st.spinner("Fetching page summary..."):
                            summary = APIClient.fetch_summary(sid)
                            st.session_state[summary_key] = summary

                    cached_summary = st.session_state[summary_key]
                    if cached_summary:
                        st.markdown(
                            f"""
                            <div style="color: #e2e8f0; font-size: 0.85rem; line-height: 1.5; padding: 8px; background: rgba(56, 189, 248, 0.05); border-radius: 8px;">
                                {cached_summary}
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    elif cached_summary is None:
                        st.caption("Click 'Generate Summary' to get an AI-powered overview of this link's content.")

            with btn_col4:
                with st.popover("🗑️ Delete", use_container_width=True):
                    if st.button(
                        "Confirm Purge",
                        key=f"del_{link_id}",
                        type="primary",
                        use_container_width=True,
                    ):
                        APIClient.delete(
                            link_id=link_id
                        )  # Fixed: calling delete, not delete_link
                        st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)

st.markdown("---")  # Visual separator

# Ensure pages is an integer for the comparison
total_pages = int(payload.get("pages", 1))

if total_pages > 1:
    p_col1, p_col2, p_col3 = st.columns([1, 2, 1])

    with p_col1:
        if st.session_state.page > 1:
            if st.button("← Previous", use_container_width=True):
                st.session_state.page -= 1
                st.rerun()

    with p_col2:
        st.markdown(
            f"""
            <div style="text-align: center; color: #94a3b8; font-weight: 600; padding-top: 10px;">
                Page {st.session_state.page} of {total_pages}
            </div>
        """,
            unsafe_allow_html=True,
        )

    with p_col3:
        if st.session_state.page < total_pages:
            if st.button("Next →", use_container_width=True):
                st.session_state.page += 1
                st.rerun()

st.caption(f"⟳ Auto-refreshes every 10s · Last updated {datetime.now().strftime('%H:%M:%S')}")
