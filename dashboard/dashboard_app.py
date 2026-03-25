import streamlit as st
import pandas as pd
import requests
import os
import sys

# Navigation & Layout Configuration
st.set_page_config(
    page_title="AI Supply Chain Control Tower",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Premium Glassmorphism Theme (CSS Injection) ---
st.markdown("""
<style>
    /* Main Background */
    .stApp {
        background: radial-gradient(circle at 10% 20%, rgb(0, 0, 0) 0%, rgb(20, 20, 30) 90.2%);
        color: #ffffff;
    }
    
    /* Card/Glassmorphism effect */
    div[data-testid="stMetricValue"] {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border-radius: 10px;
        padding: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        transition: transform 0.3s ease;
    }
    
    div[data-testid="stMetricValue"]:hover {
        transform: translateY(-5px);
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background: rgba(0, 0, 0, 0.5);
        backdrop-filter: blur(15px);
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* Custom Headers */
    h1, h2, h3 {
        background: linear-gradient(90deg, #00d2ff 0%, #3a7bd5 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800 !important;
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(90deg, #4b6cb7 0%, #182848 100%);
        color: white;
        border-radius: 20px;
        border: none;
        padding: 10px 25px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        box-shadow: 0 0 15px rgba(75, 108, 183, 0.8);
        transform: scale(1.05);
    }
    
    /* Toast styling */
    .stToast {
        backdrop-filter: blur(10px);
    }
</style>
""", unsafe_allow_html=True)

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dashboard.i18n import t, toggle_language

# Configuration
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

# --- Session State ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None
if "token" not in st.session_state:
    st.session_state.token = None
if "lang" not in st.session_state:
    st.session_state.lang = "en"

# --- Login Logic ---
if not st.session_state.logged_in:
    cols = st.columns([1, 2, 1])
    with cols[1]:
        st.title(t("log_in"))
        with st.container():
            user = st.text_input(t("username"))
            pwd = st.text_input(t("password"), type="password")
            if st.button(t("log_in")):
                resp = requests.post(f"{API_URL}/api/v1/token", json={"username": user, "password": pwd})
                if resp.status_code == 200:
                    data = resp.json()
                    st.session_state.logged_in = True
                    st.session_state.username = user
                    st.session_state.token = data["access_token"]
                    st.rerun()
                else:
                    st.error("Invalid credentials")
    st.stop()

# --- Page Definitions ---
pg = st.navigation({
    t("nav_operations"): [
        st.Page("pages/overview.py", title=t("nav_overview"), icon="📡"),
        st.Page("pages/analytics.py", title=t("nav_analytics"), icon="🚚"),
        st.Page("pages/risk_map.py", title=t("nav_risk_map"), icon="🗺️"),
    ],
    t("nav_data_lab"): [
        st.Page("pages/data_lab.py", title=t("nav_data_mgmt"), icon="🔍"),
        st.Page("pages/sim_lab.py", title=t("nav_sim_lab"), icon="🧪"),
        st.Page("pages/ai_advisor.py", title=t("nav_ai"), icon="🤖"),
    ],
    t("nav_system"): [
        st.Page("pages/admin.py", title=t("nav_admin"), icon="⚙️"),
    ]
})

# Sidebar Footer
with st.sidebar:
    st.markdown("---")
    
    # Language Toggle
    if st.button(t("lang_toggle"), key="lang_toggle_btn"):
        toggle_language()
        st.rerun()
    
    st.caption(f"Connected as: **{st.session_state.username}**")
    if st.button(t("logout")):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.token = None
        st.rerun()

# Execute Page
pg.run()
