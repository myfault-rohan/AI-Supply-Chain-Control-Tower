import streamlit as st
import requests
import pandas as pd
from dashboard.utils import API_URL

st.title("⚙️ Administrative Command")
st.markdown("### System Governance & Controls")

# --- 1. System Health ---
st.subheader("🏥 Infrastructure Health")
try:
    health_res = requests.get(f"{API_URL}/admin/system_health")
    if health_res.status_code == 200:
        health = health_res.json()
        h1, h2, h3 = st.columns(3)
        h1.metric("API Status", health["status"])
        h2.metric("Active Workspaces", health["workspaces"])
        h3.metric("System Storage", f"{health['storage_usage_mb']} MB")
except:
    st.error("Admin API unreachable.")

st.markdown("---")

# --- 2. Workspace Management ---
st.subheader("👥 User Workspace Management")
target_user = st.text_input("Username to manage", value=st.session_state.username)

if st.button("🔴 Purge Workspace Data"):
    if st.checkbox("Confirm permanent deletion of all files in this workspace"):
        res = requests.post(f"{API_URL}/admin/clear_workspace", params={"username": target_user})
        if res.status_code == 200:
            st.success(res.json()["message"])
            st.rerun()

st.markdown("---")

# --- 3. System Logs (Simulation) ---
st.subheader("📜 Recent System Activity")
logs = [
    {"timestamp": "2026-03-11 00:30:15", "component": "Backend", "event": "API Server Init", "status": "INFO"},
    {"timestamp": "2026-03-11 00:45:22", "component": "Pipeline", "event": "Triggered by 'admin' upload", "status": "SUCCESS"},
    {"timestamp": "2026-03-11 00:47:05", "component": "Forecaster", "event": "XGBoost training complete", "status": "SUCCESS"},
]
st.table(pd.DataFrame(logs))
