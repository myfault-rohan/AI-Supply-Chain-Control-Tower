import streamlit as st
import pandas as pd
import plotly.express as px
from dashboard.utils import fetch_data, no_data_view

st.title("🚚 Supply Chain Deep-Dive")
st.markdown("### Granular Operational Metrics")

tabs = st.tabs(["📦 Inventory", "🚚 Suppliers", "🏭 Warehouses", "💰 Costs"])

with tabs[0]:
    st.subheader("Inventory Distribution")
    inventory_df = fetch_data("/inventory")
    if inventory_df.empty:
        no_data_view("Inventory Metrics")
    else:
        fig = px.bar(inventory_df, x="product_id", y="current_stock", color="inventory_days", template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(inventory_df, use_container_width=True)

with tabs[1]:
    st.subheader("Supplier Reliability Matrix")
    supplier_df = fetch_data("/supplier_performance")
    if supplier_df.empty:
        no_data_view("Supplier Performance")
    else:
        fig = px.scatter(supplier_df, x="average_delay", y="reliability_score", size="total_shipments", color="supplier_status", template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(supplier_df, use_container_width=True)

with tabs[2]:
    st.subheader("Warehouse Capacity Utilization")
    wh_df = fetch_data("/warehouse_utilization")
    if wh_df.empty:
        no_data_view("Warehouse Metrics")
    else:
        st.dataframe(wh_df, use_container_width=True)
        # Utilization Gauges (Simplified for now)
        for _, row in wh_df.iterrows():
            st.write(f"**{row['warehouse_location']}**")
            st.progress(row['utilization_percent'] / 100)

with tabs[3]:
    st.subheader("Supply Chain Financial Impact")
    cost_df = fetch_data("/cost_analysis")
    if cost_df.empty:
        no_data_view("Cost Analytics")
    else:
        fig = px.treemap(cost_df, path=['product_id'], values='total_cost_impact', template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
