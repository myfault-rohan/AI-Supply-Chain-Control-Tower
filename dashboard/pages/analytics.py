import streamlit as st
import pandas as pd
import plotly.express as px
import os, sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dashboard.utils import fetch_data, no_data_view
from dashboard.i18n import t

st.title(t("analytics_title"))
st.markdown(f"### {t('analytics_subtitle')}")

tabs = st.tabs([t("tab_inventory"), t("tab_suppliers"), t("tab_warehouses"), t("tab_costs"), "ML Explainability"])

with tabs[0]:
    st.subheader(t("inventory_dist"))
    inventory_df = fetch_data("/inventory")
    if inventory_df.empty:
        no_data_view("Inventory Metrics")
    else:
        fig = px.bar(inventory_df, x="product_id", y="current_stock", 
                     color="inventory_days" if "inventory_days" in inventory_df.columns else None,
                     template="plotly_dark",
                     color_continuous_scale="RdYlGn_r")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(inventory_df, use_container_width=True)

with tabs[1]:
    st.subheader(t("supplier_matrix"))
    supplier_df = fetch_data("/supplier_performance")
    if supplier_df.empty:
        no_data_view("Supplier Performance")
    else:
        required_cols = ["average_delay", "reliability_score", "total_shipments", "supplier_status"]
        if all(c in supplier_df.columns for c in required_cols):
            fig = px.scatter(supplier_df, x="average_delay", y="reliability_score", 
                           size="total_shipments", color="supplier_status", 
                           template="plotly_dark",
                           color_discrete_map={"GOOD": "#00ff88", "WARNING": "#ffcc00", "CRITICAL": "#ff3300"})
            st.plotly_chart(fig, use_container_width=True)
        st.dataframe(supplier_df, use_container_width=True)

with tabs[2]:
    st.subheader(t("warehouse_util"))
    wh_df = fetch_data("/warehouse_utilization")
    if wh_df.empty:
        no_data_view("Warehouse Metrics")
    else:
        st.dataframe(wh_df, use_container_width=True)
        if "utilization_percent" in wh_df.columns and "warehouse_location" in wh_df.columns:
            for _, row in wh_df.iterrows():
                st.write(f"**{row['warehouse_location']}**")
                pct = min(row['utilization_percent'] / 100, 1.0)
                st.progress(pct)

with tabs[3]:
    st.subheader(t("cost_impact"))
    cost_df = fetch_data("/cost_analysis")
    if cost_df.empty:
        no_data_view("Cost Analytics")
    else:
        if "total_cost_impact" in cost_df.columns and "product_id" in cost_df.columns:
            fig = px.treemap(cost_df, path=['product_id'], values='total_cost_impact', template="plotly_dark",
                           color='total_cost_impact', color_continuous_scale="Reds")
            st.plotly_chart(fig, use_container_width=True)
        st.dataframe(cost_df, use_container_width=True)

with tabs[4]:
    st.subheader("Model Explainability (SHAP)")
    st.markdown("Understand what factors drive the demand forecasts and stockout risks.")
    
    from config import DATASET_DIR
    processed_dir = os.path.join(DATASET_DIR, "processed files")
    
    shap_summary = os.path.join(processed_dir, "shap_summary.png")
    shap_importance = os.path.join(processed_dir, "shap_importance.png")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Feature Importance**")
        if os.path.exists(shap_importance):
            st.image(shap_importance, use_container_width=True)
        else:
            st.info("Run the ML forecasting pipeline to generate SHAP feature importance plots.")
            
    with col2:
        st.markdown("**Summary Plot**")
        if os.path.exists(shap_summary):
            st.image(shap_summary, use_container_width=True)
        else:
            st.info("Run the ML forecasting pipeline to generate SHAP summary plots.")
