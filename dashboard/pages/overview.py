import streamlit as st
import pandas as pd
import plotly.express as px
import os, sys, requests, time
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dashboard.i18n import t
from config import DATASET_DIR, API_URL
PROCESSED_DIR = os.path.join(DATASET_DIR, "processed files")

st.title(t("overview"))

# Fetch Global Risk Summary
def load_df(name):
    p = os.path.join(PROCESSED_DIR, name)
    return pd.read_csv(p) if os.path.exists(p) else pd.DataFrame()

risk_summary = load_df("global_risk_summary.csv")

if risk_summary.empty:
    st.info(t("no_data"))
else:
    # Key Metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(t("critical_products"), risk_summary["critical_products"].iloc[0] if "critical_products" in risk_summary else 0)
    m2.metric(t("unreliable_suppliers") if t("unreliable_suppliers") != "unreliable_suppliers" else "Unreliable Suppliers", risk_summary["unreliable_suppliers"].iloc[0] if "unreliable_suppliers" in risk_summary else 0)
    m3.metric(t("overloaded_warehouses") if t("overloaded_warehouses") != "overloaded_warehouses" else "Overloaded Warehouses", risk_summary["overloaded_warehouses"].iloc[0] if "overloaded_warehouses" in risk_summary else 0)
    m4.metric(t("high_cost_risk") if t("high_cost_risk") != "high_cost_risk" else "High Cost Risk", f"${risk_summary['high_cost_products'].iloc[0] if 'high_cost_products' in risk_summary else 0}k")

    # Download PDF Report Button
    st.markdown("---")
    if st.button("Download Executive Report"):
        try:
            res = requests.get(f"{API_URL}/export/pdf", timeout=30)
            if res.status_code == 200:
                st.download_button(
                    "💾 Save PDF",
                    data=res.content,
                    file_name="executive_report.pdf",
                    mime="application/pdf"
                )
            else:
                st.warning("Failed to generate PDF. Make sure backend is running.")
        except Exception as e:
            st.error(f"Report error: {e}")

    st.markdown("---")

    # Upgrade 9: Live KPI alert toasts
    if "alert_snooze_time" not in st.session_state:
        st.session_state["alert_snooze_time"] = 0
        st.session_state["alert_history"] = []

    health_df = load_df("supply_chain_health.csv")
    if not health_df.empty:
        current_time = time.time()
        # Snooze for 60 mins (3600 seconds)
        if current_time - st.session_state["alert_snooze_time"] > 3600:
            new_alerts = []
            for _, row in health_df.iterrows():
                pid = row["product_id"]
                if row["health_status"] == "CRITICAL":
                    st.toast(f"CRITICAL: {pid}", icon="🚨")
                    new_alerts.append({"time": datetime.now().strftime("%H:%M:%S"), "pid": pid, "status": "CRITICAL"})
                elif row["health_status"] == "WARNING":
                    st.toast(f"WARNING: {pid}", icon="⚠️")
                    new_alerts.append({"time": datetime.now().strftime("%H:%M:%S"), "pid": pid, "status": "WARNING"})
            
            # Prepend to history, keep last 10
            st.session_state["alert_history"] = (new_alerts + st.session_state["alert_history"])[:10]
            st.session_state["alert_snooze_time"] = current_time

    # Sidebar Alert History
    with st.sidebar:
        st.markdown("### 🔔 Alert History")
        if st.button("Snooze Alerts (60m)"):
            st.session_state["alert_snooze_time"] = time.time()
            st.success("Alerts snoozed!")
            
        for alert in st.session_state["alert_history"]:
            color = "red" if alert["status"] == "CRITICAL" else "orange"
            st.markdown(f"**{alert['time']}** - <span style='color:{color}'>{alert['status']}</span>: {alert['pid']}", unsafe_allow_html=True)

    # Health Distribution
    st.subheader(t("health_score"))
    if not health_df.empty and "health_status" in health_df.columns:
        fig_health = px.pie(
            health_df, 
            names='health_status', 
            hole=0.4,
            color='health_status',
            color_discrete_map={'GOOD': '#00ff88', 'WARNING': '#ffcc00', 'CRITICAL': '#ff3300'}
        )
        st.plotly_chart(fig_health, use_container_width=True)
