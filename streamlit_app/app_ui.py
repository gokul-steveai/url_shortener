import requests
import streamlit as st
import os
from datetime import datetime
from st_copy_to_clipboard import st_copy_to_clipboard
from streamlit_autorefresh import st_autorefresh

API_URL = os.getenv("API_URL", "http://localhost:8000")
PAGE_SIZE = 20

st.set_page_config(
    page_title="BoltLink | Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Auto-refresh interval
st_autorefresh(interval=15_000, key="engagement_refresh")

st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
    .main { background: radial-gradient(circle at 50% 0%, #1e293b 0%, #0f172a 100%); color: #f8fafc; }
    .hero-title {
        font-size: 3rem; font-weight: 800;
        background: linear-gradient(90deg, #fff 0%, #38bdf8 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        text-align: center; margin-bottom: 0.25rem;
    }
    .role-badge-user {
        display: inline-block; padding: 3px 14px; border-radius: 50px;
        font-size: 0.7rem; font-weight: 700; text-transform: uppercase;
        background: rgba(56,189,248,0.12); color: #38bdf8;
        border: 1px solid rgba(56,189,248,0.3);
    }
    .role-badge-admin {
        display: inline-block; padding: 3px 14px; border-radius: 50px;
        font-size: 0.7rem; font-weight: 700; text-transform: uppercase;
        background: rgba(251,146,60,0.12); color: #fb923c;
        border: 1px solid rgba(251,146,60,0.3);
    }
    .link-card {
        background: rgba(30,41,59,0.4); border: 1px solid rgba(255,255,255,0.05);
        backdrop-filter: blur(12px); border-radius: 20px; padding: 1.25rem;
        margin-bottom: 0.75rem; transition: all 0.3s ease;
    }
    .link-card:hover {
        background: rgba(30,41,59,0.65); border-color: rgba(56,189,248,0.35);
        box-shadow: 0 16px 32px -16px rgba(0,0,0,0.5);
    }
    .user-row {
        background: rgba(30,41,59,0.35); border: 1px solid rgba(255,255,255,0.05);
        border-radius: 14px; padding: 0.9rem 1.2rem; margin-bottom: 0.5rem;
    }
    .status-pill {
        padding: 3px 10px; border-radius: 50px; font-size: 0.65rem; font-weight: 700;
        text-transform: uppercase; background: rgba(56,189,248,0.1); color: #38bdf8;
        border: 1px solid rgba(56,189,248,0.2);
    }
    .admin-pill {
        padding: 3px 10px; border-radius: 50px; font-size: 0.65rem; font-weight: 700;
        text-transform: uppercase; background: rgba(251,146,60,0.1); color: #fb923c;
        border: 1px solid rgba(251,146,60,0.2);
    }
    [data-testid="metric-container"] {
        background: rgba(255,255,255,0.03) !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        backdrop-filter: blur(8px); padding: 1.25rem !important; border-radius: 18px !important;
    }
    .stButton > button {
        border-radius: 12px !important;
        background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%) !important;
        border: none !important; font-weight: 600 !important;
        padding: 0.5rem 1.5rem !important; transition: 0.25s ease !important;
    }
    .stButton > button:hover { transform: scale(1.02); box-shadow: 0 0 18px rgba(14,165,233,0.4) !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; background: rgba(255,255,255,0.03); border-radius: 12px; padding: 4px; }
    .stTabs [data-baseweb="tab"] { border-radius: 10px !important; font-weight: 600 !important; }
    div[data-testid="stSidebar"] { display: none; }
</style>
""",
    unsafe_allow_html=True,
)


# ── Helpers ────────────────────────────────────────────────────────────────────
def api_call(method, endpoint, json=None, headers=None):
    try:
        res = requests.request(
            method, f"{API_URL}{endpoint}", json=json, headers=headers, timeout=10
        )
        res.raise_for_status()
        return res.json()
    except requests.exceptions.HTTPError as e:
        st.error(
            f"Error {e.response.status_code}: {e.response.json().get('detail', str(e))}"
        )
        return None
    except Exception as e:
        st.error(f"API Error: {e}")
        return None


def format_date(date_str: str) -> str:
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00")).strftime(
            "%d %b %Y"
        )
    except Exception:
        return date_str or "—"


def auth_headers():
    return {"Authorization": f"Bearer {st.session_state.access_token}"}


# ── Auth State ─────────────────────────────────────────────────────────────────

for key in ("access_token", "user", "page"):
    if key not in st.session_state:
        st.session_state[key] = None if key != "page" else 1


def logout():
    for key in ("access_token", "user", "page"):
        st.session_state[key] = None if key != "page" else 1
    st.rerun()


# ── Login / Register ───────────────────────────────────────────────────────────

if not st.session_state.access_token:
    st.markdown('<div class="hero-title">⚡ BoltLink</div>', unsafe_allow_html=True)
    st.markdown(
        "<p style='text-align:center;color:#94a3b8;margin-bottom:2rem;'>Enterprise-grade URL shortening & analytics</p>",
        unsafe_allow_html=True,
    )

    col = st.columns([1, 2, 1])[1]
    with col:
        tab_login, tab_register = st.tabs(["Login", "Register"])

        with tab_login:
            with st.form("login_form"):
                email = st.text_input("Email", placeholder="you@example.com")
                password = st.text_input("Password", type="password")
                if st.form_submit_button("Login", use_container_width=True):
                    res = api_call(
                        "POST",
                        "/auth/login",
                        json={"email": email, "password": password},
                    )
                    if res:
                        st.session_state.access_token = res["access_token"]
                        st.session_state.user = api_call(
                            "GET", "/auth/me", headers=auth_headers()
                        )
                        st.rerun()

        with tab_register:
            with st.form("register_form"):
                email = st.text_input("Email", placeholder="you@example.com")
                password = st.text_input("Password (min 8 chars)", type="password")
                if st.form_submit_button("Create Account", use_container_width=True):
                    res = api_call(
                        "POST",
                        "/auth/register",
                        json={"email": email, "password": password},
                    )
                    if res:
                        st.session_state.access_token = res["access_token"]
                        st.session_state.user = api_call(
                            "GET", "/auth/me", headers=auth_headers()
                        )
                        st.rerun()
    st.stop()


# ── Shared Header ──────────────────────────────────────────────────────────────

user = st.session_state.user
is_admin = user and user.get("role") == "admin"
badge_cls = "role-badge-admin" if is_admin else "role-badge-user"
badge_label = "Admin" if is_admin else "User"

st.markdown('<div class="hero-title">⚡ BoltLink</div>', unsafe_allow_html=True)
st.markdown(
    f"<p style='text-align:center;color:#94a3b8;margin-bottom:1.5rem;'>"
    f"{user['email']} &nbsp;<span class='{badge_cls}'>{badge_label}</span></p>",
    unsafe_allow_html=True,
)

hdr_l, hdr_r = st.columns([8, 1])
with hdr_r:
    if st.button("Logout", use_container_width=True):
        logout()

st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

if is_admin:
    admin_stats = api_call("GET", "/admin/stats", headers=auth_headers())
    users_list = api_call("GET", "/admin/users", headers=auth_headers())

    # ── Platform Metrics ──────────────────────────────────────────────────────
    if admin_stats:
        st.markdown("### 🌐 Platform Overview")
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Users", admin_stats["total_users"])
        c2.metric("Total Links", admin_stats["total_links"])
        c3.metric("Total Engagements", admin_stats["total_clicks"])
        st.markdown("<br>", unsafe_allow_html=True)

    # ── User Management ───────────────────────────────────────────────────────
    st.markdown("### 👥 User Management")

    if users_list:
        search = st.text_input(
            "Search users", placeholder="Filter by email…", label_visibility="collapsed"
        )
        filtered = (
            [u for u in users_list if search.lower() in u["email"].lower()]
            if search
            else users_list
        )

        for u in filtered:
            pill = "admin-pill" if u["role"] == "admin" else "status-pill"
            active_dot = "🟢" if u["is_active"] else "🔴"
            joined = format_date(u.get("created_at", ""))

            with st.container():
                st.markdown(
                    f"""
<div class="user-row">
  <div style="display:flex;justify-content:space-between;align-items:center;">
    <div>
      <span style="font-weight:700;color:#f1f5f9;">{u['email']}</span>
      &nbsp;<span class="{pill}">{u['role']}</span>
      &nbsp;{active_dot}
    </div>
    <div style="color:#64748b;font-size:0.8rem;">ID #{u['id']} &nbsp;·&nbsp; Joined {joined}</div>
  </div>
</div>""",
                    unsafe_allow_html=True,
                )

                a1, a2, a3, _ = st.columns([1, 1, 1, 4])
                with a1:
                    new_role = "user" if u["role"] == "admin" else "admin"
                    label = "→ User" if u["role"] == "admin" else "→ Admin"
                    if st.button(
                        label, key=f"role_{u['id']}", use_container_width=True
                    ):
                        api_call(
                            "PATCH",
                            f"/admin/users/{u['id']}/role?role={new_role}",
                            headers=auth_headers(),
                        )
                        st.rerun()
                with a2:
                    with st.popover("🗑️ Delete", use_container_width=True):
                        st.warning(f"Delete **{u['email']}** and all their links?")
                        if st.button(
                            "Confirm Delete",
                            key=f"del_user_{u['id']}",
                            type="primary",
                            use_container_width=True,
                        ):
                            api_call(
                                "DELETE",
                                f"/admin/users/{u['id']}",
                                headers=auth_headers(),
                            )
                            st.rerun()

    st.caption(
        f"⟳ Auto-refreshes every 10s · Last updated {datetime.now().strftime('%H:%M:%S')}"
    )
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# USER DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

# ── Create Link ───────────────────────────────────────────────────────────────
with st.container():
    col_in, col_btn = st.columns([5, 1])
    with col_in:
        url_input = st.text_input(
            "URL",
            placeholder="https://your-very-long-url.com",
            label_visibility="collapsed",
        )
    with col_btn:
        if st.button("⚡ Shorten", use_container_width=True):
            if url_input:
                res = api_call(
                    "POST",
                    "/shorten",
                    json={"target_url": url_input},
                    headers=auth_headers(),
                )
                if res:
                    st.balloons()
                    st.success(f"✅ {res['short_url']}")

# ── Stats ─────────────────────────────────────────────────────────────────────
stats = api_call("GET", "/stats", headers=auth_headers())
payload = api_call(
    "GET",
    f"/links?page={st.session_state.page}&limit={PAGE_SIZE}",
    headers=auth_headers(),
)

if stats:
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("Your Links", stats["total_links"])
    c2.metric("Total Engagement", stats["total_clicks"])
    c3.metric("Page", st.session_state.page)

# ── Links List ────────────────────────────────────────────────────────────────
st.markdown("### 🔗 Your Links")

if not payload:
    st.stop()

raw_items = payload.get("items", []) if isinstance(payload, dict) else []
items = [i for i in raw_items if isinstance(i, dict)]

if not items:
    st.info("No links yet. Paste a URL above to create your first short link.")
else:
    for link in items:
        sid = link.get("short_id")
        link_id = link.get("id")
        clicks = link.get("clicks", 0)
        target = link.get("original_url", "")
        created = format_date(link.get("created_at", ""))

        st.markdown(
            f"""
<div class="link-card">
  <div style="display:flex;justify-content:space-between;align-items:center;">
    <div style="overflow:hidden;flex:1;">
      <div style="display:flex;align-items:center;gap:8px;">
        <span style="font-size:1.3rem;font-weight:800;color:#38bdf8;">/{sid}</span>
        <span class="status-pill">Active</span>
      </div>
      <div style="color:#94a3b8;font-size:0.82rem;font-family:monospace;
                  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:4px;">
        {target}
      </div>
    </div>
    <div style="text-align:right;min-width:110px;margin-left:16px;">
      <div style="font-size:1.5rem;font-weight:800;color:#f1f5f9;">{clicks}</div>
      <div style="font-size:0.6rem;color:#475569;text-transform:uppercase;letter-spacing:1px;">Clicks</div>
      <div style="font-size:0.68rem;color:#64748b;margin-top:2px;">{created}</div>
    </div>
  </div>
</div>""",
            unsafe_allow_html=True,
        )

        b1, b2, b3, b4, _ = st.columns([1, 1, 1, 1, 3])
        with b1:
            st.link_button("🌐 Open", f"{API_URL}/{sid}", use_container_width=True)
        with b2:
            st_copy_to_clipboard(
                f"{API_URL}/{sid}",
                before_copy_label="📋 Copy",
                after_copy_label="✅ Copied",
            )
        with b3:
            with st.popover("🤖 Summary", use_container_width=True):
                key = f"summary_{link_id}"
                if key not in st.session_state:
                    st.session_state[key] = None
                if st.button(
                    "Generate", key=f"gen_{link_id}", use_container_width=True
                ):
                    with st.spinner("Generating AI summary…"):
                        res = api_call(
                            "GET", f"/links/{sid}/summary", headers=auth_headers()
                        )
                        st.session_state[key] = res.get("summary") if res else None
                if st.session_state[key]:
                    st.markdown(
                        f'<div style="color:#e2e8f0;font-size:0.83rem;line-height:1.55;padding:8px;background:rgba(56,189,248,0.05);border-radius:8px;">{st.session_state[key]}</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.caption("Click Generate to get an AI-powered page overview.")
        with b4:
            with st.popover("🗑️ Delete", use_container_width=True):
                if st.button(
                    "Confirm Delete",
                    key=f"del_{link_id}",
                    type="primary",
                    use_container_width=True,
                ):
                    api_call("DELETE", f"/links/{link_id}", headers=auth_headers())
                    st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

# ── Pagination ────────────────────────────────────────────────────────────────
st.markdown("---")
total_pages = int(payload.get("pages", 1))
if total_pages > 1:
    p1, p2, p3 = st.columns([1, 2, 1])
    with p1:
        if st.session_state.page > 1:
            if st.button("← Previous", use_container_width=True):
                st.session_state.page -= 1
                st.rerun()
    with p2:
        st.markdown(
            f'<div style="text-align:center;color:#94a3b8;font-weight:600;padding-top:10px;">Page {st.session_state.page} of {total_pages}</div>',
            unsafe_allow_html=True,
        )
    with p3:
        if st.session_state.page < total_pages:
            if st.button("Next →", use_container_width=True):
                st.session_state.page += 1
                st.rerun()

st.caption(
    f"⟳ Auto-refreshes every 15s · Last updated {datetime.now().strftime('%H:%M:%S')}"
)
