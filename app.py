"""
app.py
Truck Utilization Tracker -- Streamlit app.

Run locally:
    streamlit run app.py

Default login (only needed to UPDATE data -- the dashboard is open to view for everyone):
    username: user   password: user123
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta

import db
import analytics
from excel_export import export_day_wise_to_excel_bytes, build_report_dataframe

st.set_page_config(
    page_title="Truck Utilization Tracker",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed",
)
db.init_db()

# ---------------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------------
if "screen" not in st.session_state:
    st.session_state.screen = "landing"   # landing -> login -> update_home / dashboard
if "username" not in st.session_state:
    st.session_state.username = None
if "theme" not in st.session_state:
    st.session_state.theme = "light"
if "last_submit_success" not in st.session_state:
    st.session_state.last_submit_success = None


def go(screen):
    st.session_state.screen = screen


def logout():
    st.session_state.screen = "landing"
    st.session_state.username = None


def toggle_theme():
    st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"


# ---------------------------------------------------------------------------
# Theme palette
# ---------------------------------------------------------------------------
def get_theme_colors():
    dark = st.session_state.theme == "dark"
    if dark:
        return dict(
            page_bg_1="#0b1120", page_bg_2="#141c30", secondary_bg="#1e293b",
            text_color="#f8fafc", subtitle_color="#cbd5e1",
            card_glass="rgba(30, 41, 59, 0.55)", card_border="#334155",
            form_bg="#1e293b", form_border="#334155",
            badge_bg="#1e3a5f", badge_text="#bfdbfe",
            accent_from="#3b82f6", accent_to="#60a5fa",
            alert_text="#1f2937", color_scheme="dark",
            yellow_border="rgba(250, 204, 21, 0.55)",
            yellow_glow="0 0 0 2px rgba(250, 204, 21, 0.12), 0 10px 34px rgba(250, 204, 21, 0.20), 0 4px 18px rgba(0, 0, 0, 0.35)",
            yellow_glow_soft="0 0 0 1px rgba(250, 204, 21, 0.30), 0 8px 24px rgba(250, 204, 21, 0.15)",
        )
    return dict(
        page_bg_1="#f8fafc", page_bg_2="#eef2fb", secondary_bg="#f4f6fb",
        text_color="#1f2937", subtitle_color="#4b5563",
        card_glass="rgba(255, 255, 255, 0.55)", card_border="#e5e9f2",
        form_bg="#ffffff", form_border="#e5e9f2",
        badge_bg="#eef2fb", badge_text="#1F3864",
        accent_from="#1F3864", accent_to="#2E75B6",
        alert_text="#1f2937", color_scheme="light",
        yellow_border="rgba(217, 119, 6, 0.45)",
        yellow_glow="0 0 0 2px rgba(250, 204, 21, 0.18), 0 10px 30px rgba(250, 204, 21, 0.25), 0 4px 16px rgba(31, 56, 100, 0.10)",
        yellow_glow_soft="0 0 0 1px rgba(217, 119, 6, 0.20), 0 6px 18px rgba(217, 119, 6, 0.12)",
    )


# ---------------------------------------------------------------------------
# Global styling
# ---------------------------------------------------------------------------
def render_css():
    T = get_theme_colors()

    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap');

        :root, .stApp {{
            --background-color: {T['page_bg_1']};
            --secondary-background-color: {T['secondary_bg']};
            --text-color: {T['text_color']};
            --primary-color: {T['accent_from']};
            color-scheme: {T['color_scheme']};
        }}

        html, body, [class*="css"] {{
            font-family: 'Inter', sans-serif;
            color: {T['text_color']};
        }}

        .stApp {{
            background:
                radial-gradient(circle at 12% -10%, rgba(250, 204, 21, 0.10), transparent 45%),
                radial-gradient(circle at 90% 110%, rgba(46, 117, 182, 0.12), transparent 45%),
                linear-gradient(160deg, {T['page_bg_1']} 0%, {T['page_bg_2']} 55%, {T['page_bg_1']} 100%);
            background-attachment: fixed;
        }}

        h1, h2, h3, .hero-title {{
            font-family: 'Poppins', sans-serif !important;
        }}

        #MainMenu, footer, header {{visibility: hidden;}}

        .block-container {{
            padding-top: 1.5rem;
            padding-bottom: 2rem;
            max-width: 1280px;
        }}

        .hero-title {{
            font-size: 2.3rem;
            font-weight: 700;
            background: linear-gradient(90deg, {T['accent_from']}, {T['accent_to']});
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.2rem;
        }}

        .hero-subtitle {{
            color: {T['subtitle_color']} !important;
            font-size: 1.05rem;
            text-align: center;
            margin: 0.5rem 0 1.8rem 0;
        }}

        [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {{
            color: {T['subtitle_color']} !important;
        }}

        /* ---- Glassy, yellow-bordered cards (landing) ---- */
        .nav-icon {{ font-size: 3.4rem; margin-bottom: 0.5rem; }}
        .nav-title {{ font-family: 'Poppins', sans-serif; font-weight: 700; font-size: 1.6rem; color: {T['accent_from']}; }}
        .nav-desc {{ color: {T['subtitle_color']}; font-size: 1.05rem; margin-top: 0.6rem; }}

        [class*="st-key-card_update"], [class*="st-key-card_dashboard"], [class*="st-key-card_pro"] {{
            background: {T['card_glass']};
            backdrop-filter: blur(14px);
            -webkit-backdrop-filter: blur(14px);
            border: 1.5px solid {T['yellow_border']};
            box-shadow: {T['yellow_glow']};
            border-radius: 24px;
            padding: 2.6rem 2rem 1.8rem 2rem;
            height: 420px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            align-items: center;
            text-align: center;
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }}
        [class*="st-key-card_update"]:hover, [class*="st-key-card_dashboard"]:hover, [class*="st-key-card_pro"]:hover {{
            transform: translateY(-4px);
        }}

        /* ---- Professional Dashboard: colored KPI boxes ---- */
        .kpi-box {{
            border-radius: 14px;
            padding: 1.1rem 1rem;
            text-align: center;
            background: {T['form_bg']};
            border: 2px solid;
        }}
        .kpi-box .kpi-value {{ font-family: 'Poppins', sans-serif; font-weight: 700; font-size: 2.1rem; }}
        .kpi-box .kpi-label {{ color: {T['subtitle_color']}; font-size: 0.8rem; font-weight: 600; margin-top: 0.2rem; letter-spacing: 0.02em; }}
        .kpi-blue {{ border-color: #2E75B6; }} .kpi-blue .kpi-value {{ color: #2E75B6; }}
        .kpi-green {{ border-color: #22c55e; }} .kpi-green .kpi-value {{ color: #22c55e; }}
        .kpi-orange {{ border-color: #f59e0b; }} .kpi-orange .kpi-value {{ color: #f59e0b; }}
        .kpi-red {{ border-color: #ef4444; }} .kpi-red .kpi-value {{ color: #ef4444; }}

        /* ---- Colored section header bars (Top Performers / Needs Focus) ---- */
        .section-header {{
            padding: 0.55rem 1rem;
            border-radius: 10px;
            font-weight: 700;
            text-align: center;
            color: white !important;
            margin-bottom: 0.5rem;
            font-size: 0.95rem;
            letter-spacing: 0.02em;
        }}
        .section-header.green {{ background: linear-gradient(90deg, #15803d, #22c55e); }}
        .section-header.red {{ background: linear-gradient(90deg, #b91c1c, #ef4444); }}

        /* ---- Region Scorecard container ---- */
        .scorecard-box {{
            background: {T['card_glass']};
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid {T['form_border']};
            border-radius: 16px;
            padding: 1.2rem;
        }}
        .scorecard-title {{
            text-align: center;
            font-weight: 700;
            background: linear-gradient(90deg, {T['accent_from']}, {T['accent_to']});
            color: white !important;
            padding: 0.55rem;
            border-radius: 10px;
            margin-bottom: 1rem;
        }}

        .highlight-box {{
            border-radius: 12px;
            padding: 0.9rem 1.1rem;
            margin-bottom: 0.6rem;
            font-size: 0.92rem;
            border-left: 4px solid;
        }}
        .highlight-good {{ background: rgba(34,197,94,0.12); border-color: #22c55e; color: {T['text_color']}; }}
        .highlight-warning {{ background: rgba(245,158,11,0.14); border-color: #f59e0b; color: {T['text_color']}; }}

        .target-banner {{
            background: linear-gradient(90deg, {T['accent_from']}, {T['accent_to']});
            color: white !important;
            text-align: center;
            border-radius: 14px;
            padding: 1rem 1.2rem;
            font-weight: 600;
            margin: 1rem 0 1.5rem 0;
        }}

        /* ---- Glassy login box ---- */
        [class*="st-key-login_box"] {{
            background: {T['card_glass']};
            backdrop-filter: blur(14px);
            -webkit-backdrop-filter: blur(14px);
            border: 1.5px solid {T['yellow_border']};
            box-shadow: {T['yellow_glow']};
            border-radius: 20px;
            padding: 1.8rem;
            max-width: 460px;
            margin: 0 auto;
        }}
        [class*="st-key-login_box"] div[data-testid="stForm"] {{
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
        }}

        /* ---- Regular forms (Edit) and the Add Entry container also get a soft glass+gold look ---- */
        div[data-testid="stForm"], [class*="st-key-add_entry_box"] {{
            background: {T['card_glass']};
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1.5px solid {T['yellow_border']};
            box-shadow: {T['yellow_glow_soft']};
            border-radius: 16px;
            padding: 1.5rem;
        }}
        div[data-testid="stForm"] label, div[data-testid="stForm"] p,
        [class*="st-key-add_entry_box"] label, [class*="st-key-add_entry_box"] p,
        .stRadio label, .stTextInput label, .stNumberInput label,
        .stSelectbox label, .stDateInput label,
        [data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] p,
        [data-testid="stWidgetLabel"] label {{
            color: {T['text_color']} !important;
            opacity: 1 !important;
        }}

        /* Radio option text -- Streamlit sometimes dims unselected options via
           opacity, which combined with a light theme can make them unreadable */
        [data-testid="stRadio"] label,
        [data-testid="stRadio"] label p,
        [data-testid="stRadio"] label div,
        [data-testid="stRadio"] label span,
        [role="radiogroup"] label,
        [role="radiogroup"] label p {{
            color: {T['text_color']} !important;
            opacity: 1 !important;
        }}

        /* ---- Buttons (default, full-size, used inside cards / forms) ---- */
        div[data-testid="stButton"] > button, div[data-testid="stFormSubmitButton"] > button {{
            border-radius: 10px;
            font-weight: 600;
            padding: 0.55rem 1rem;
            border: none;
            background: linear-gradient(90deg, {T['accent_from']}, {T['accent_to']});
            color: white !important;
            transition: opacity 0.15s ease;
        }}
        div[data-testid="stButton"] > button:hover, div[data-testid="stFormSubmitButton"] > button:hover {{
            opacity: 0.88;
        }}
        div[data-testid="stButton"] > button p, div[data-testid="stFormSubmitButton"] > button p {{
            color: white !important;
        }}

        /* ---- Small circular icon buttons (theme toggle / back / logout / home) ---- */
        [class*="st-key-topbar_"] div[data-testid="stButton"] > button {{
            width: 44px;
            height: 44px;
            border-radius: 50% !important;
            padding: 0 !important;
            font-size: 1.15rem;
            line-height: 1;
        }}
        [class*="st-key-topbar_"] div[data-testid="stButton"] > button p {{
            font-size: 1.15rem;
            margin: 0;
        }}

        .badge-pill {{
            display: inline-block;
            background: {T['badge_bg']};
            color: {T['badge_text']} !important;
            border-radius: 999px;
            padding: 0.25rem 0.9rem;
            font-size: 0.85rem;
            font-weight: 600;
            margin-bottom: 1rem;
        }}

        div[data-testid="stMetric"] {{
            background: {T['form_bg']};
            border: 1px solid {T['form_border']};
            border-radius: 12px;
            padding: 0.8rem;
        }}
        div[data-testid="stMetricLabel"], div[data-testid="stMetricLabel"] * {{
            color: {T['subtitle_color']} !important;
        }}
        div[data-testid="stMetricValue"], div[data-testid="stMetricValue"] * {{
            color: {T['text_color']} !important;
        }}

        div[data-testid="stAlert"], div[data-testid="stAlert"] * {{
            color: {T['alert_text']} !important;
        }}

        button[data-testid="stTab"],
        [data-testid="stTabs"] button,
        .stTabs button,
        button[data-baseweb="tab"] {{
            color: {T['subtitle_color']} !important;
            opacity: 1 !important;
        }}
        button[data-testid="stTab"] p,
        [data-testid="stTabs"] button p,
        .stTabs button p,
        button[data-baseweb="tab"] p {{
            color: inherit !important;
            opacity: 1 !important;
        }}
        button[data-testid="stTab"][aria-selected="true"],
        [data-testid="stTabs"] button[aria-selected="true"],
        .stTabs button[aria-selected="true"],
        button[data-baseweb="tab"][aria-selected="true"] {{
            color: {T['accent_from']} !important;
            font-weight: 700;
        }}

        details {{
            background: {T['form_bg']};
            border: 1px solid {T['form_border']};
            border-radius: 12px;
        }}
        summary, details p, details span, details label {{
            color: {T['text_color']} !important;
        }}

        [data-testid="stDataFrame"] {{
            border-radius: 12px;
            overflow: hidden;
        }}

        .app-footer {{
            text-align: center;
            color: {T['subtitle_color']};
            opacity: 0.85;
            font-size: 0.82rem;
            margin-top: 2.5rem;
            padding-top: 1.2rem;
            border-top: 1px solid {T['form_border']};
        }}

        @media (max-width: 640px) {{
            .hero-title {{ font-size: 1.7rem; }}
            .block-container {{ padding-left: 0.8rem; padding-right: 0.8rem; }}
            [class*="st-key-card_update"], [class*="st-key-card_dashboard"], [class*="st-key-card_pro"] {{
                height: auto;
                min-height: 260px;
                padding: 1.6rem 1.2rem 1.3rem 1.2rem;
            }}
            .nav-icon {{ font-size: 2.6rem; }}
            .nav-title {{ font-size: 1.25rem; }}
            .nav-desc {{ font-size: 0.92rem; }}
        }}

        @media (min-width: 641px) and (max-width: 1024px) {{
            [class*="st-key-card_update"], [class*="st-key-card_dashboard"], [class*="st-key-card_pro"] {{
                height: 380px;
            }}
        }}
    </style>
    """, unsafe_allow_html=True)


def header(title, subtitle=None, centered=True):
    align = "center" if centered else "left"
    st.markdown(f'<div class="hero-title" style="text-align:{align};">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="hero-subtitle">{subtitle}</div>', unsafe_allow_html=True)


_SHORTCUT_ICONS = {
    "update_home": "📝",
    "dashboard": "📊",
    "professional_dashboard": "📈",
}


def render_topbar(action_icon=None, action_fn=None):
    """Small icon-only buttons, top-right: quick-jump shortcuts to the other two
    main sections (if the current screen is one of the three), theme toggle,
    and an optional contextual action (logout / home / back)."""
    current = st.session_state.screen
    shortcuts = [(scr, icon) for scr, icon in _SHORTCUT_ICONS.items() if scr != current] \
        if current in _SHORTCUT_ICONS else []

    n_icons = len(shortcuts) + 1 + (1 if action_icon else 0)  # +1 for theme toggle
    with st.container(key=f"topbar_{current}"):
        widths = [12 - n_icons] + [1] * n_icons
        cols = st.columns(widths)
        i = 1
        for scr, icon in shortcuts:
            with cols[i]:
                if st.button(icon, key=f"shortcut_icon_{scr}_from_{current}", use_container_width=True):
                    if scr == "update_home" and not st.session_state.username:
                        go("login")
                    else:
                        go(scr)
                    st.rerun()
            i += 1
        with cols[i]:
            theme_icon = "☀️" if st.session_state.theme == "dark" else "🌙"
            if st.button(theme_icon, key=f"theme_icon_{current}", use_container_width=True):
                toggle_theme()
                st.rerun()
        i += 1
        if action_icon:
            with cols[i]:
                if st.button(action_icon, key=f"action_icon_{current}", use_container_width=True):
                    action_fn()
                    st.rerun()


def render_footer():
    st.markdown(
        f'<div class="app-footer">© {datetime.now().year} Truck Utilization Tracker — Built for RCPL Beverages Operations</div>',
        unsafe_allow_html=True,
    )


render_css()


# ---------------------------------------------------------------------------
# Landing screen: title top-left, theme icon top-right, centered subtitle,
# two equal glassy square cards with the action button pinned to the bottom
# ---------------------------------------------------------------------------
def screen_landing():
    spacer, col_icon = st.columns([9, 1])
    with col_icon:
        with st.container(key="topbar_landing"):
            icon = "☀️" if st.session_state.theme == "dark" else "🌙"
            if st.button(icon, key="theme_icon_landing", use_container_width=True):
                toggle_theme()
                st.rerun()

    st.markdown('<div class="hero-title" style="text-align:center;">Truck Utilization Tracker</div>', unsafe_allow_html=True)

    st.markdown(
        '<div class="hero-subtitle">Track dedicated vehicle (DV) availability and utilization across all plants, in real time.</div>',
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3, gap="large")
    with col1:
        with st.container(key="card_update"):
            st.markdown(
                '<div class="nav-icon">📝</div>'
                '<div class="nav-title">Update Data</div>'
                '<div class="nav-desc">Update today\'s DV Data.</div>',
                unsafe_allow_html=True,
            )
            if st.button("Go to Update Data", use_container_width=True, key="landing_update_btn"):
                go("login")
                st.rerun()

    with col2:
        with st.container(key="card_dashboard"):
            st.markdown(
                '<div class="nav-icon">📊</div>'
                '<div class="nav-title">View Report</div>'
                '<div class="nav-desc">See the latest utilization report</div>',
                unsafe_allow_html=True,
            )
            if st.button("View Reports", use_container_width=True, key="landing_dashboard_btn"):
                go("dashboard")
                st.rerun()

    with col3:
        with st.container(key="card_pro"):
            st.markdown(
                '<div class="nav-icon">📈</div>'
                '<div class="nav-title">Trend Dashboard</div>'
                '<div class="nav-desc">Weekly/monthly trends</div>',
                unsafe_allow_html=True,
            )
            if st.button("Open Analytics", use_container_width=True, key="landing_pro_btn"):
                go("professional_dashboard")
                st.rerun()

    render_footer()


# ---------------------------------------------------------------------------
# Login screen (only gate before data-entry)
# ---------------------------------------------------------------------------
def screen_login():
    render_topbar("←", lambda: go("landing"))
    header("Login to Update Data")
    st.markdown(
        '<div style="text-align:center;"><span class="badge-pill">Login required for updates only</span></div>',
        unsafe_allow_html=True,
    )
    st.write("")

    with st.container(key="login_box"):
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)

        if st.button("← Back to Home", use_container_width=True, key="login_back_btn"):
            go("landing")
            st.rerun()

    if submitted:
        if db.check_login(username, password):
            st.session_state.username = username
            go("update_home")
            st.rerun()
        else:
            st.error("Invalid username or password.")

    render_footer()


# ---------------------------------------------------------------------------
# Update Data flow: Add Entry  +  Edit / Delete Entries
# ---------------------------------------------------------------------------
def screen_update_home():
    render_topbar("🚪", logout)
    header("Update Truck Utilization Data")
    st.markdown(
        f'<div style="text-align:center;"><span class="badge-pill">Logged in as {st.session_state.username}</span></div>',
        unsafe_allow_html=True,
    )
    st.write("")

    tab_add, tab_edit = st.tabs(["➕ Add Entry", "✏️ Edit / Delete Entries"])

    with tab_add:
        _render_add_entry_form()

    with tab_edit:
        _render_edit_delete()

    render_footer()


def _render_add_entry_form():
    with st.container(key="add_entry_box"):
        col1, col2 = st.columns(2)
        with col1:
            entry_date = st.date_input("Date", value=date.today(), key="add_entry_date")
        with col2:
            shift = st.radio("Shift", db.SHIFTS, horizontal=True, key="add_entry_shift")

        updater_name = st.text_input("Updater name", key="add_entry_updater")

        region = st.radio("Factory Region", db.REGIONS, horizontal=True, key="add_entry_region")

        region_plants = db.get_plants_by_region(region)
        if not region_plants:
            st.warning(f"No plants configured for the {region} region.")
            return

        site_code_options = [p["site_code"] for p in region_plants]
        plant_by_code = {p["site_code"]: p["plant_name"] for p in region_plants}

        selected_site_code = st.selectbox(
            "Plant Name (type to search)",
            options=site_code_options,
            format_func=lambda sc: f"{plant_by_code[sc]} ({sc})",
            key="add_entry_plant",
        )
        st.markdown(
            f'<span class="badge-pill">Site Code: {selected_site_code}</span>',
            unsafe_allow_html=True,
        )
        st.write("")

        dv_type = st.selectbox("DV Type", options=db.DV_TYPES, key="add_entry_dv_type")
        st.caption("Submitting again for the same plant with a different DV Type adds a separate, segregated entry.")

        st.markdown("**Data (all numbers):**")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            total_dv = st.number_input("Total DV", min_value=0, step=1, key="add_entry_total")
        with c2:
            dv_available = st.number_input("DV Available for Today", min_value=0, step=1, key="add_entry_avail")
        with c3:
            dv_utilised = st.number_input("DV Utilised (Orders Recd)", min_value=0, step=1, key="add_entry_util")
        with c4:
            dv_inroute = st.number_input("DV Inroute to Plant", min_value=0, step=1, key="add_entry_inroute")

        submitted = st.button("Submit Update", use_container_width=True, key="add_entry_submit_btn")

    if submitted:
        plant_name = plant_by_code[selected_site_code]
        if not updater_name.strip():
            st.error("Please enter the updater name.")
        elif dv_utilised > dv_available:
            st.error("DV Utilised cannot exceed DV Available for today. Please check the numbers.")
        else:
            plant_id = db.get_plant_id_by_site_code(selected_site_code)
            db.add_entry(
                plant_id=plant_id,
                entry_date=entry_date.isoformat(),
                shift=shift,
                dv_type=dv_type,
                total_dv=int(total_dv),
                dv_available=int(dv_available),
                dv_utilised=int(dv_utilised),
                dv_inroute=int(dv_inroute),
                updated_by=updater_name.strip(),
                updated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
            )
            balance = dv_available - dv_utilised
            pct = (dv_utilised / dv_available * 100) if dv_available else 0
            st.session_state.last_submit_success = {
                "plant": plant_name, "region": region, "dv_type": dv_type,
                "balance": balance, "pct": pct,
            }

    if st.session_state.last_submit_success:
        info = st.session_state.last_submit_success
        st.success(
            f"Saved: {info['plant']} ({info['region']}) — DV Type: {info['dv_type']} — "
            f"Unutilized Balance: {info['balance']}, Utilization: {info['pct']:.0f}%"
        )
        if st.button("📊 View Dashboard", use_container_width=True, key="post_submit_dashboard"):
            st.session_state.last_submit_success = None
            go("dashboard")
            st.rerun()


def _render_edit_delete():
    dates = db.get_dates_with_entries()
    if not dates:
        st.info("No entries submitted yet. Add one in the 'Add Entry' tab first.")
        return

    most_recent = datetime.strptime(max(dates), "%Y-%m-%d").date()
    selected_date_obj = st.date_input(
        "Select a date to review its entries", value=most_recent, key="edit_date_select"
    )
    selected_date = selected_date_obj.isoformat()
    entries = db.get_entries_for_date(selected_date)

    if not entries:
        st.info(f"No entries for {selected_date}.")
        return

    st.caption(f"{len(entries)} entr{'y' if len(entries)==1 else 'ies'} found for {selected_date}. Expand one to edit or delete it.")

    for entry in entries:
        label = (
            f"🏭 {entry['plant_name']} ({entry['region']}) — {entry['shift']} — "
            f"DV Type: {entry['dv_type']} — by {entry['updated_by']}"
        )
        with st.expander(label):
            edit_key = f"edit_form_{entry['id']}"
            with st.form(edit_key):
                st.caption(f"Site Code: {entry['site_code']} | Submitted: {entry['updated_at']}")
                ec1, ec2, ec3, ec4 = st.columns(4)
                with ec1:
                    e_total = st.number_input("Total DV", min_value=0, step=1,
                                               value=entry["total_dv"], key=f"tot_{entry['id']}")
                with ec2:
                    e_avail = st.number_input("DV Available", min_value=0, step=1,
                                               value=entry["dv_available"], key=f"avail_{entry['id']}")
                with ec3:
                    e_util = st.number_input("DV Utilised", min_value=0, step=1,
                                              value=entry["dv_utilised"], key=f"util_{entry['id']}")
                with ec4:
                    e_inroute = st.number_input("DV Inroute", min_value=0, step=1,
                                                 value=entry["dv_inroute"], key=f"inroute_{entry['id']}")
                e_updater = st.text_input("Corrected by (your name)", value=entry["updated_by"],
                                           key=f"updater_{entry['id']}")
                save_clicked = st.form_submit_button("💾 Save Changes", use_container_width=True)

            if save_clicked:
                if e_util > e_avail:
                    st.error("DV Utilised cannot exceed DV Available.")
                else:
                    db.update_entry(
                        entry_id=entry["id"], total_dv=int(e_total), dv_available=int(e_avail),
                        dv_utilised=int(e_util), dv_inroute=int(e_inroute),
                        updated_by=e_updater.strip() or entry["updated_by"],
                        updated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
                    )
                    st.success("Entry updated.")
                    st.rerun()

            st.divider()
            confirm_key = f"confirm_delete_{entry['id']}"
            if not st.session_state.get(confirm_key):
                if st.button("🗑️ Delete This Entry", key=f"del_btn_{entry['id']}"):
                    st.session_state[confirm_key] = True
                    st.rerun()
            else:
                st.warning("Delete this entry permanently? This cannot be undone.")
                dc1, dc2 = st.columns(2)
                with dc1:
                    if st.button("Yes, delete it", key=f"confirm_yes_{entry['id']}", use_container_width=True):
                        db.delete_entry(entry["id"])
                        st.session_state[confirm_key] = False
                        st.success("Entry deleted.")
                        st.rerun()
                with dc2:
                    if st.button("Cancel", key=f"confirm_no_{entry['id']}", use_container_width=True):
                        st.session_state[confirm_key] = False
                        st.rerun()


# ---------------------------------------------------------------------------
# Dashboard -- open to everyone, no login
# ---------------------------------------------------------------------------
def screen_dashboard():
    render_topbar("🏠", lambda: go("landing"))
    header("Truck Utilization Dashboard", "Latest data submitted across all plants.")

    latest = db.get_latest_entries()

    if not latest:
        st.info("No data has been submitted yet. Go to **Update Data** to add the first entry.")
        render_footer()
        return

    tab1, tab2, tab3 = st.tabs([
        "📅 Day-wise Report", "📜 All Updates Log", "🕒 Plant History"
    ])

    with tab1:
        _render_day_wise_report()

    with tab2:
        _render_all_updates_log()

    with tab3:
        _render_plant_history(latest)

    render_footer()


def _full_table_height(n_rows: int) -> int:
    """Sizes the dataframe box tall enough to show every row with no inner scrollbar."""
    return 38 * (n_rows + 1) + 3


def _styled_table(display_rows):
    df = pd.DataFrame(display_rows)

    def highlight(row):
        if row.get("Region") == "Pan India Total":
            return ["background-color: #1F3864; color: white; font-weight: bold"] * len(row)
        if "Total" in str(row.get("Region", "")):
            return ["background-color: #D9E1F2; color: #1F3864; font-weight: bold"] * len(row)
        return [""] * len(row)

    st.dataframe(
        df.style.apply(highlight, axis=1),
        use_container_width=True, hide_index=True,
        height=_full_table_height(len(df)),
    )


def _render_plant_history(latest):
    plant_names = sorted({e["plant_name"] for e in latest})
    selected_plant = st.selectbox("Select a plant to see its update history", plant_names)
    history = db.get_entry_history(selected_plant)
    hist_df = pd.DataFrame(history)[
        ["entry_date", "shift", "dv_type", "updated_at", "updated_by", "total_dv",
         "dv_available", "dv_utilised", "dv_inroute"]
    ]
    hist_df.columns = ["Date", "Shift", "DV Type", "Submitted At", "Updated By", "Total DV",
                        "DV Available", "DV Utilised", "DV Inroute"]
    st.dataframe(hist_df, use_container_width=True, hide_index=True,
                 height=_full_table_height(len(hist_df)))


def _render_all_updates_log():
    st.caption("Every single update ever submitted, most recent first.")
    log = db.get_all_entries_log()
    if not log:
        st.info("No updates submitted yet.")
        return

    df = pd.DataFrame(log)[[
        "entry_date", "shift", "dv_type", "region", "site_code", "plant_name",
        "total_dv", "dv_available", "dv_utilised", "dv_inroute",
        "updated_by", "updated_at",
    ]]
    df.columns = ["Date", "Shift", "DV Type", "Region", "Site Code", "Plant", "Total DV",
                  "DV Available", "DV Utilised", "DV Inroute", "Updated By", "Submitted At"]
    st.dataframe(df, use_container_width=True, hide_index=True,
                 height=_full_table_height(len(df)))

    buf_df = df.copy()
    excel_bytes = _simple_df_to_excel_bytes(buf_df)
    st.download_button(
        "⬇️ Download Full Log as Excel", data=excel_bytes,
        file_name=f"truck_utilization_full_log_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )


def _render_day_wise_report():
    dates = db.get_dates_with_entries()
    if not dates:
        st.info("No data submitted yet.")
        return

    most_recent = datetime.strptime(max(dates), "%Y-%m-%d").date()
    selected_date_obj = st.date_input("Select a date", value=most_recent, key="dashboard_day_select")
    selected_date = selected_date_obj.isoformat()

    # Shifts are recorded on the backend but not segregated in the visible report --
    # only the latest submission per plant (+ DV Type) for the day is shown here.
    entries = db.get_latest_entries_for_date(selected_date)

    if not entries:
        st.info("No entries submitted for this date.")
        return

    rows = build_report_dataframe(entries)
    display_rows = [{
        "Region": r["Region"], "Site Code": r["Site Code"], "Plant": r["Plant"],
        "DV Type": r["DV Type"],
        "Total DV": r["Total DV"], "DV Available": r["DV Available"],
        "DV Utilised": r["DV Utilised"], "DV Inroute": r["DV Inroute"],
        "Unutilized Balance": r["Unutilized Balance"],
        "Utilization %": f"{r['Utilization %']*100:.0f}%",
        "Opening DV %": f"{r['Opening DV %']*100:.0f}%",
        "Effective Utilization %": f"{r['Effective Utilization %']*100:.0f}%",
    } for r in rows]
    _styled_table(display_rows)

    excel_bytes = export_day_wise_to_excel_bytes(selected_date, entries)
    st.download_button(
        f"⬇️ Download {selected_date} Report as Excel", data=excel_bytes,
        file_name=f"truck_utilization_{selected_date}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        key="day_wise_download",
    )


def _simple_df_to_excel_bytes(df: pd.DataFrame) -> bytes:
    import io
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Full Log")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Professional Dashboard -- weekly/monthly trend analytics, open to everyone
# ---------------------------------------------------------------------------
def _kpi_box(color_class, value, label):
    st.markdown(
        f'<div class="kpi-box {color_class}">'
        f'<div class="kpi-value">{value}</div>'
        f'<div class="kpi-label">{label}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _month_bounds(year: int, month: int):
    import calendar
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def screen_professional_dashboard():
    render_topbar("🏠", lambda: go("landing"))
    header("Professional Dashboard", "Dedicated Vehicle (DV) utilization — trend analytics for leadership review.")

    today = date.today()
    period = st.radio("Trend", ["Weekly", "Monthly"], horizontal=True, key="pro_dash_period")

    if period == "Weekly":
        default_from = today - timedelta(days=today.weekday())  # most recent Monday
        col1, col2 = st.columns(2)
        with col1:
            from_date = st.date_input("From date", value=default_from, key="pro_week_from")
        with col2:
            to_date = st.date_input("To date", value=today, key="pro_week_to")
        if from_date > to_date:
            st.error("'From date' must be on or before 'To date'.")
            render_footer()
            return
        range_label = f"{from_date.strftime('%d %b %Y')} – {to_date.strftime('%d %b %Y')} · Pan India Fleet"

    else:  # Monthly
        dates_with_data = db.get_dates_with_entries()
        month_keys = sorted({d[:7] for d in dates_with_data}, reverse=True) or [today.strftime("%Y-%m")]
        month_labels = {
            ym: datetime.strptime(ym + "-01", "%Y-%m-%d").strftime("%B %Y") for ym in month_keys
        }
        selected_month = st.selectbox(
            "Month", month_keys, format_func=lambda ym: month_labels[ym], key="pro_month_select"
        )
        yr, mo = int(selected_month[:4]), int(selected_month[5:7])
        from_date, month_end = _month_bounds(yr, mo)
        to_date = min(month_end, today)
        range_label = f"{month_labels[selected_month]} · Pan India Fleet"

    entries = db.get_entries_between(from_date.isoformat(), to_date.isoformat())
    data = analytics.build_dashboard_data(entries)

    st.markdown(
        f'<div style="text-align:center;"><span class="badge-pill">{range_label}</span></div>',
        unsafe_allow_html=True,
    )
    st.write("")

    if data is None:
        st.info("No data submitted yet in this period. Add entries in **Update Data** first.")
        render_footer()
        return

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        _kpi_box("kpi-blue", f"{data['avg_fleet_size']:.0f}", "AVG FLEET SIZE (# DV / DAY)")
    with k2:
        _kpi_box("kpi-green", f"{data['avg_utilization_pct']:.0f}%", "UTILIZATION vs AVAILABLE DV")
    with k3:
        _kpi_box("kpi-orange", f"{data['avg_opening_pct']:.0f}%", "OPENING DV % (TARGET ≥ 50%)")
    with k4:
        _kpi_box("kpi-red", f"~{data['avg_trips_per_dv_month']:.0f}", "TRIPS / DV / MONTH (TARGET 15)")

    st.caption(f"Based on {data['days_count']} day(s) of submitted data in this period.")
    st.write("")

    # ---- Top performers / plants needing focus ----
    col_top, col_bottom = st.columns(2)
    with col_top:
        st.markdown('<div class="section-header green">★ TOP PERFORMING PLANTS</div>', unsafe_allow_html=True)
        top_df = data["plant_avg"].head(5)[["plant_name", "region", "util_pct"]].copy()
        top_df["Utilization %"] = (top_df["util_pct"] * 100).round(0).astype(int).astype(str) + "%"
        top_df = top_df.rename(columns={"plant_name": "Plant", "region": "Region"})[["Plant", "Region", "Utilization %"]]
        st.dataframe(top_df, use_container_width=True, hide_index=True, height=_full_table_height(len(top_df)))

    with col_bottom:
        st.markdown('<div class="section-header red">⚠ PLANTS NEEDING FOCUS</div>', unsafe_allow_html=True)
        bottom_df = data["bottom5"][["plant_name", "region", "util_pct"]].copy()
        bottom_df["Utilization %"] = (bottom_df["util_pct"] * 100).round(0).astype(int).astype(str) + "%"
        bottom_df = bottom_df.rename(columns={"plant_name": "Plant", "region": "Region"})[["Plant", "Region", "Utilization %"]]
        st.dataframe(bottom_df, use_container_width=True, hide_index=True, height=_full_table_height(len(bottom_df)))

    with st.expander("See all plants"):
        all_df = data["plant_avg"][["plant_name", "region", "util_pct", "opening_pct", "eff_util"]].copy()
        for col in ["util_pct", "opening_pct", "eff_util"]:
            all_df[col] = (all_df[col] * 100).round(0).astype(int).astype(str) + "%"
        all_df.columns = ["Plant", "Region", "Utilization %", "Opening DV %", "Effective Utilization %"]
        st.dataframe(all_df, use_container_width=True, hide_index=True, height=_full_table_height(len(all_df)))

    st.write("")

    # ---- Region scorecard ----
    st.markdown('<div class="scorecard-box">', unsafe_allow_html=True)
    st.markdown(f'<div class="scorecard-title">📍 REGION SCORECARD ({period.upper()})</div>', unsafe_allow_html=True)
    region_df = data["region_avg"].copy()
    for col in ["util_pct", "opening_pct", "eff_util"]:
        region_df[col] = (region_df[col] * 100).round(0).astype(int).astype(str) + "%"
    region_df = region_df.rename(columns={
        "region": "Region", "util_pct": "Utilization %",
        "opening_pct": "Opening DV %", "eff_util": "Effective Utilization %",
    })
    st.dataframe(region_df, use_container_width=True, hide_index=True, height=_full_table_height(len(region_df)))
    st.markdown('</div>', unsafe_allow_html=True)

    st.write("")

    # ---- Key highlights ----
    st.markdown('<div class="scorecard-title">🔑 KEY HIGHLIGHTS</div>', unsafe_allow_html=True)
    highlights = analytics.generate_highlights(data)
    if not highlights:
        st.caption("Not enough data yet to generate highlights.")
    for kind, text in highlights:
        css_class = "highlight-good" if kind == "good" else "highlight-warning"
        icon = "✅" if kind == "good" else "⚠️"
        st.markdown(f'<div class="highlight-box {css_class}">{icon} {text}</div>', unsafe_allow_html=True)

    st.markdown(
        '<div class="target-banner">Let\'s turn every DV around faster — ≥50% Opening DV Availability = 15 trips/month = fixed cost recovered.</div>',
        unsafe_allow_html=True,
    )

    render_footer()


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
screen = st.session_state.screen
if screen == "landing":
    screen_landing()
elif screen == "login":
    screen_login()
elif screen == "update_home":
    screen_update_home()
elif screen == "dashboard":
    screen_dashboard()
elif screen == "professional_dashboard":
    screen_professional_dashboard()
