import streamlit as st
import requests

# --- Global Variables ---
API_URL = "http://localhost:8000"

# --- Page Configuration ---
st.set_page_config(
    page_title="BoltLink | Intelligence in every click",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- Custom Elegant Styling ---
st.markdown(
    """
    <style>
    /* Global Styles */
    .main { background: #0e1117; color: #ffffff; }
    
    /* Card Styling */
    .link-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 20px;
        border-radius: 15px;
        margin-bottom: 20px;
        transition: transform 0.2s;
    }
    .link-card:hover {
        transform: translateY(-5px);
        border-color: #00d4ff;
    }
    
    /* Modern Buttons */
    .stButton>button {
        background: linear-gradient(90deg, #00d4ff 0%, #0072ff 100%);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        box-shadow: 0 0 15px rgba(0, 212, 255, 0.5);
    }
    
    /* Metric Boxes */
    [data-testid="stMetricValue"] { color: #00d4ff; }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Header Section ---
st.markdown(
    "<h1 style='text-align: center; color: white;'>⚡ BoltLink</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='text-align: center; color: #888;'>Premium URL Shortening & Content Intelligence</p>",
    unsafe_allow_html=True,
)

# --- Main Action Area ---
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    with st.container():
        st.markdown('<div class="link-card">', unsafe_allow_html=True)
        url_input = st.text_input(
            "Destination URL",
            placeholder="https://app.yourbrand.com/long-path-to-resource",
        )

        c1, c2 = st.columns([3, 1])
        with c2:
            shorten_btn = st.button("Shorten 🚀")

        if shorten_btn:
            if url_input:
                try:
                    # Logic to call your FastAPI /shorten endpoint
                    response = requests.post(
                        f"{API_URL}/shorten", json={"target_url": url_input}
                    )
                    if response.status_code == 200:
                        data = response.json()
                        st.balloons()
                        st.success("Your link is ready!")
                        st.code(data["short_url"], language="text")
                    else:
                        st.error("Failed to generate link.")
                except:
                    st.error("Backend offline. Please check Docker.")
        st.markdown("</div>", unsafe_allow_html=True)

st.divider()

# --- Dashboard Metrics ---
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Links", "1,284", "+12")
m2.metric("Total Clicks", "45.2k", "14%")
m3.metric("Avg. Latency", "14ms", "-2ms")
m4.metric("AI Summaries", "892", "+5")

# --- Interactive Link Management ---
st.write("### 📂 Managed Links")


# Function to fetch real data from your FastAPI backend
def fetch_real_links():
    try:
        response = requests.get(f"{API_URL}/links")
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        st.error(f"Error connecting to backend: {e}")
        return []


# --- Inside your Dashboard Logic ---
links_data = fetch_real_links()

# Integration Logic: Fetch live data from your /links endpoint
try:
    if not links_data:
        st.info("No links found in the database. Start shortening!")
    else:
        for link in links_data:
            with st.container():
                st.markdown(
                    f"""
                    <div class="link-card">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <span style="color: #00d4ff; font-weight: bold; font-size: 1.2em;">/{link['id']}</span>
                                <br/>
                                <small style="color: #888;">{link['url']}</small>
                            </div>
                            <div style="text-align: right;">
                                <span style="font-size: 1.1em; color: white;">📊 {link['clicks']} clicks</span>
                                <br/>
                                <small style="color: #666;">{link['date']}</small>
                            </div>
                        </div>
                    </div>
                """,
                    unsafe_allow_html=True,
                )

            # Action Buttons under each link
            b1, b2, b3, _ = st.columns([1, 1, 1, 5])
            with b1:
                st.button("Copy", key=f"cp_{link['id']}")
            with b2:
                st.button("AI Info", key=f"ai_{link['id']}")
            with b3:
                st.button("Delete", key=f"del_{link['id']}")

except Exception as e:
    st.info("Start your FastAPI server to view live link data.")
