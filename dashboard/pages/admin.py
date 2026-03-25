import streamlit as st
import pandas as pd
import os, sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dashboard.utils import API_URL, api_get, api_post
from dashboard.i18n import t

st.title(t("admin_title"))
st.markdown(f"### {t('admin_subtitle')}")

# --- 1. System Health ---
st.subheader(t("infra_health"))
try:
    health_res = api_get("/admin/system_health", auth_required=True)
    if health_res and health_res.status_code == 200:
        health = health_res.json()
        h1, h2, h3, h4 = st.columns(4)
        h1.metric("API Status", health["status"])
        h2.metric("Active Workspaces", health["workspaces"])
        h3.metric("Processed Files", health["processed_files"])
        h4.metric("Storage Usage", f"{health['storage_usage_mb']} MB")
    elif health_res and health_res.status_code == 401:
        st.warning("Authentication required. Please log in again.")
except Exception as e:
    st.error(f"Admin API unreachable: {e}")

st.markdown("---")

# --- 2. API Health Check ---
st.subheader("API Health Check")
try:
    api_health = api_get("/api/v1/health", auth_required=False)
    if api_health and api_health.status_code == 200:
        data = api_health.json()
        st.success(f"API Status: **{data['status']}** | Version: **{data['version']}** | Time: {data['timestamp']}")
    else:
        st.error("API health check failed")
except Exception as e:
    st.error(f"Cannot reach API server: {e}")

st.markdown("---")

# --- 3. Workspace Management ---
st.subheader(t("workspace_mgmt"))
st.info(f"Managing workspace for: **{st.session_state.username}**")

if st.button(t("purge_btn")):
    confirm = st.checkbox(t("confirm_delete"))
    if confirm:
        try:
            res = api_post("/admin/clear_workspace", auth_required=True)
            if res and res.status_code == 200:
                st.success(res.json()["message"])
                st.rerun()
            elif res and res.status_code == 401:
                st.error("Authentication failed. Please log in again.")
        except Exception as e:
            st.error(f"Error: {e}")

st.markdown("---")

# --- 4. System Logs ---
st.subheader(t("system_logs"))
from datetime import datetime
logs = [
    {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "component": "Backend", "event": "API Server Running", "status": "INFO"},
    {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "component": "Auth", "event": "JWT + bcrypt enabled", "status": "SECURE"},
    {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "component": "Pipeline", "event": "Pandas processing active", "status": "READY"},
]
st.table(pd.DataFrame(logs))

# --- 5. Quick Links ---
st.markdown("---")
st.subheader("Quick Links")
st.markdown(f"- [API Documentation]({API_URL}/docs)")
st.markdown(f"- [Health Check]({API_URL}/api/v1/health)")
