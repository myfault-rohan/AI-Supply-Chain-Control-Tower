import streamlit as st
import pandas as pd
import plotly.express as px
from dashboard.utils import fetch_data, no_data_view, glass_card

st.title("🌐 Commander's Overview")
st.markdown("### Real-Time Strategic Intelligence")

# Fetch Global Risk Summary
risk_summary = fetch_data("/global_risk_summary")

if risk_summary.empty:
    no_data_view("Global Risk Overview")
else:
    # Key Metrics
    m1, m2, m3, m4 = st.columns(4)
    with m1: glass_card("Critical Products", risk_summary["critical_products"][0], color="inverse")
    with m2: glass_card("Unreliable Suppliers", risk_summary["unreliable_suppliers"][0], color="inverse")
    with m3: glass_card("Overloaded Warehouses", risk_summary["overloaded_warehouses"][0], color="inverse")
    with m4: glass_card("High Cost Risk", f"${risk_summary['high_cost_products'][0]}k", color="inverse")

    st.markdown("---")

    # Live Monitoring Section
    st.subheader("📡 Live Inventory Pulse")
    live_data = fetch_data("/live_inventory")
    
    if not live_data.empty:
        col1, col2 = st.columns([1, 2])
        with col1:
            st.dataframe(live_data.head(10), use_container_width=True)
        with col2:
            fig = px.line(live_data, y="current_stock", title="Real-Time Stock Fluctuations", template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Waiting for live Spark stream...")

    st.markdown("---")

    # Health Distribution
    st.subheader("🌡️ Network Health Distribution")
    health_data = fetch_data("/health")
    if not health_data.empty:
        fig_health = px.pie(
            health_data, 
            names='health_status', 
            hole=0.4,
            color='health_status',
            color_discrete_map={'GOOD': '#00ff88', 'WARNING': '#ffcc00', 'CRITICAL': '#ff3300'},
            template="plotly_dark"
        )
        st.plotly_chart(fig_health, use_container_width=True)
