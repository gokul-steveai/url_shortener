from datetime import datetime

import requests
import streamlit as st
import os

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
    page_title="BoltLink",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =========================================================
# SESSION STATE
# =========================================================

if "page" not in st.session_state:
    st.session_state.page = 1

# =========================================================
# STYLING
# =========================================================

st.markdown(
    """
<style>

/* =========================================================
GLOBAL
========================================================= */

html, body, [class*="css"] {
    font-family: Inter, sans-serif;
}

.main {
    background-color: #0f172a;
    color: white;
}

/* =========================================================
HEADER
========================================================= */

.hero-container {
    text-align: center;
    padding: 2rem 0 3rem 0;
}

.hero-title {
    font-size: 3rem;
    font-weight: 800;
    color: white;
    margin-bottom: 0.5rem;
}

.hero-subtitle {
    color: #94a3b8;
    font-size: 1rem;
}

/* =========================================================
CARD
========================================================= */

.link-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 18px;
    padding: 1.2rem;
    margin-bottom: 1rem;
    transition: all 0.2s ease;
}

.link-card:hover {
    transform: translateY(-3px);
    border-color: #38bdf8;
    background: rgba(255,255,255,0.06);
}

/* =========================================================
BUTTONS
========================================================= */

.stButton > button {
    width: 100%;
    border-radius: 10px;
    border: none;
    background: linear-gradient(
        135deg,
        #0ea5e9,
        #2563eb
    );
    color: white;
    font-weight: 600;
    height: 42px;
    transition: 0.2s ease;
}

.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 0 20px rgba(14,165,233,0.35);
}

/* =========================================================
INPUTS
========================================================= */

.stTextInput > div > div > input {
    border-radius: 12px;
    background: rgba(255,255,255,0.04);
    color: white;
    border: 1px solid rgba(255,255,255,0.08);
}

/* =========================================================
METRICS
========================================================= */

[data-testid="metric-container"] {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    padding: 1rem;
    border-radius: 16px;
}

[data-testid="stMetricValue"] {
    color: #38bdf8;
}

/* =========================================================
PAGINATION
========================================================= */

.pagination-container {
    margin-top: 2rem;
    text-align: center;
}

</style>
""",
    unsafe_allow_html=True,
)

# =========================================================
# API HELPERS
# =========================================================


class APIClient:
    @staticmethod
    def shorten_url(target_url: str):
        response = requests.post(
            f"{API_URL}/shorten",
            json={"target_url": target_url},
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        return response.json()

    @staticmethod
    def fetch_links(page: int, limit: int):
        response = requests.get(
            f"{API_URL}/links",
            params={
                "page": page,
                "limit": limit,
            },
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        return response.json()

    @staticmethod
    def delete_link(link_id: int):
        response = requests.delete(
            f"{API_URL}/links/{link_id}",
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()


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

# =========================================================
# SHORTENER
# =========================================================

with st.container():
    st.markdown('<div class="link-card">', unsafe_allow_html=True)

    st.subheader("Create Short Link")

    col1, col2 = st.columns([5, 1])

    with col1:
        url_input = st.text_input(
            "Destination URL",
            placeholder="https://yourdomain.com/resource",
            label_visibility="collapsed",
        )

    with col2:
        shorten_clicked = st.button(
            "Shorten",
            use_container_width=True,
        )

    if shorten_clicked:
        if not url_input.strip():
            st.warning("Please enter a valid URL.")
        else:
            try:
                payload = APIClient.shorten_url(url_input)

                st.success("Short URL generated successfully")

                st.code(
                    payload["short_url"],
                    language="text",
                )

            except requests.HTTPError as e:
                st.error(f"Request failed: {e.response.text}")

            except requests.RequestException:
                st.error("Backend service unavailable.")

    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# FETCH LINKS
# =========================================================

try:
    payload = APIClient.fetch_links(
        page=st.session_state.page,
        limit=PAGE_SIZE,
    )

    items = payload.get("items", [])
    total = payload.get("total", 0)
    pages = payload.get("pages", 1)

except requests.RequestException:
    st.error("Failed to connect to backend.")
    st.stop()

# =========================================================
# METRICS
# =========================================================

total_clicks = sum(item.get("clicks", 0) for item in items)

metric1, metric2, metric3 = st.columns(3)

metric1.metric(
    "Total Links",
    total,
)

metric2.metric(
    "Page Clicks",
    total_clicks,
)

metric3.metric(
    "Current Page",
    st.session_state.page,
)

# =========================================================
# LINKS
# =========================================================

st.markdown("## Managed Links")

if not items:
    st.info("No shortened URLs found.")
else:
    for link in items:

        short_code = link.get("short_id", link["id"])

        created_at = format_date(link.get("created_at", ""))

        st.markdown(
            f"""
<div class="link-card">

<div style="
display:flex;
justify-content:space-between;
gap:1rem;
flex-wrap:wrap;
">

<div>

<div style="
font-size:1.1rem;
font-weight:700;
color:#38bdf8;
margin-bottom:0.4rem;
">
/{short_code}
</div>

<div style="
color:#cbd5e1;
font-size:0.92rem;
word-break:break-all;
">
{link.get("target_url", "")}
</div>

</div>

<div style="text-align:right; min-width:120px;">

<div style="
font-size:1rem;
font-weight:700;
color:white;
">
📊 {link.get("clicks", 0)}
</div>

<div style="
color:#94a3b8;
font-size:0.85rem;
margin-top:0.3rem;
">
{created_at}
</div>

</div>

</div>

</div>
""",
            unsafe_allow_html=True,
        )

        action1, action2, action3, _ = st.columns([1, 1, 1, 4])

        short_url = f"{API_URL}/{short_code}"

        with action1:
            st.link_button(
                "Open",
                short_url,
                use_container_width=True,
            )

        with action2:
            if st.button(
                "Copy",
                key=f"copy_{link['id']}",
                use_container_width=True,
            ):
                st.toast("Link copied")

        with action3:
            if st.button(
                "Delete",
                key=f"delete_{link['id']}",
                use_container_width=True,
            ):
                try:
                    APIClient.delete_link(link["id"])

                    st.success("Link deleted")

                    st.rerun()

                except requests.RequestException:
                    st.error("Failed to delete link.")

# =========================================================
# PAGINATION
# =========================================================

if pages > 1:

    st.markdown(
        '<div class="pagination-container">',
        unsafe_allow_html=True,
    )

    prev_col, page_col, next_col = st.columns([1, 2, 1])

    with prev_col:
        if st.session_state.page > 1:
            st.button(
                "← Previous",
                on_click=change_page,
                args=[st.session_state.page - 1],
                use_container_width=True,
            )

    with page_col:
        st.markdown(
            f"""
<div style="
text-align:center;
padding-top:0.6rem;
color:#cbd5e1;
font-weight:600;
">
Page {st.session_state.page} of {pages}
</div>
""",
            unsafe_allow_html=True,
        )

    with next_col:
        if st.session_state.page < pages:
            st.button(
                "Next →",
                on_click=change_page,
                args=[st.session_state.page + 1],
                use_container_width=True,
            )

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )
