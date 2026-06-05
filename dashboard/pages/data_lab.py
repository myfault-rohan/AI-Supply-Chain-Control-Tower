import streamlit as st
import pandas as pd
import os
import shutil
import time
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import sys

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import DATASET_DIR
from backend.pandas_processor import run_full_pipeline

DEMO_DIR = os.path.join(DATASET_DIR, "demo_data")
PROCESSED_DIR = os.path.join(DATASET_DIR, "processed files")

def get_workspace_dir(username):
    # Fallback to default if username is somehow None
    uname = username if username else "default"
    return os.path.join(DATASET_DIR, "workspaces", uname)

def data_lab_page():
    st.title("Data Management Lab 🔍")
    username = st.session_state.get("username", "default")
    workspace_dir = get_workspace_dir(username)
    os.makedirs(workspace_dir, exist_ok=True)

    # --- SECTION 1: File Upload ---
    st.header("1. Upload Supply Chain Data")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded_files = st.file_uploader(
            "Upload supply chain files", 
            type=["csv", "xlsx", "json"], 
            accept_multiple_files=True
        )
        if uploaded_files:
            for file in uploaded_files:
                file_path = os.path.join(workspace_dir, file.name)
                with open(file_path, "wb") as f:
                    f.write(file.getbuffer())
            st.success(f"Successfully uploaded {len(uploaded_files)} files!")

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Load Demo Data", use_container_width=True):
            if os.path.exists(DEMO_DIR):
                for f in os.listdir(DEMO_DIR):
                    shutil.copy2(os.path.join(DEMO_DIR, f), os.path.join(workspace_dir, f))
                st.success("Demo data loaded!")
                st.rerun()
            else:
                st.error("Demo data directory not found.")
                
        if st.button("Clear Workspace", use_container_width=True):
            shutil.rmtree(workspace_dir)
            os.makedirs(workspace_dir, exist_ok=True)
            st.success("Workspace cleared!")
            st.rerun()

    st.subheader("Staged Files")
    staged_files = [f for f in os.listdir(workspace_dir) if f.endswith(('.csv', '.xlsx', '.json'))]
    if staged_files:
        st.write(", ".join(staged_files))
    else:
        st.info("No files in workspace.")

    st.markdown("---")

    # --- SECTION 2: Run Pipeline ---
    st.header("2. Analysis Pipeline")
    
    if st.button("Run Full Analysis Pipeline", type="primary", use_container_width=True):
        if not staged_files:
            st.warning("Please upload files first.")
            return

        progress_bar = st.progress(0, text="Initializing pipeline...")
        steps = [
            "Reading workspace files", "Detecting data types", "Building supply chain dataset",
            "Forecasting demand", "Generating reorder recommendations", "Calculating health scores",
            "Evaluating supplier performance", "Analyzing warehouse utilization", "Computing cost impact"
        ]
        for i, step in enumerate(steps):
            time.sleep(0.1)
            progress_bar.progress((i + 1) / len(steps), text=step)
            
        result = run_full_pipeline(username)
        progress_bar.empty()
        
        if result.get("success"):
            st.success(f"Pipeline complete! Processed {result['rows_processed']} rows across {result['products']} products. CRITICAL alerts: {result['critical_alerts']}")
            st.session_state["pipeline_run"] = True
            time.sleep(1)
            st.rerun()
        else:
            st.error(f"Pipeline Failed: {result.get('error')}")

    # --- SECTION 3: Results ---
    if st.session_state.get("pipeline_run") or os.path.exists(os.path.join(PROCESSED_DIR, "global_risk_summary.csv")):
        st.markdown("---")
        st.header("3. Results Analysis")
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
            "Health Overview", "Inventory & Demand", "Reorder Alerts", 
            "Suppliers", "Warehouses", "Cost Analysis", "Raw Data Explorer"
        ])
        
        def load_df(name):
            p = os.path.join(PROCESSED_DIR, name)
            return pd.read_csv(p) if os.path.exists(p) else pd.DataFrame()

        df_health = load_df("supply_chain_health.csv")
        df_demand = os.path.join(DATASET_DIR, "demand_predictions.csv")
        df_demand = pd.read_csv(df_demand) if os.path.exists(df_demand) else pd.DataFrame()
        df_reorder = load_df("reorder_recommendations.csv")
        df_sup = load_df("supplier_performance.csv")
        df_ware = load_df("warehouse_utilization.csv")
        df_cost = load_df("cost_analysis.csv")

        with tab1:
            st.subheader("Health Overview")
            if not df_health.empty:
                col_a, col_b = st.columns(2)
                with col_a:
                    fig_pie = px.pie(df_health, names="health_status", title="Health Status Distribution",
                                     color="health_status", color_discrete_map={"GOOD": "green", "WARNING": "orange", "CRITICAL": "red"})
                    st.plotly_chart(fig_pie, use_container_width=True)
                with col_b:
                    fig_bar = px.bar(df_health, x="product_id", y="days_until_stockout", title="Days Until Stockout")
                    fig_bar.add_hline(y=7, line_dash="dash", line_color="orange")
                    fig_bar.add_hline(y=3, line_dash="dash", line_color="red")
                    st.plotly_chart(fig_bar, use_container_width=True)
                st.dataframe(df_health, use_container_width=True)

        with tab2:
            st.subheader("Inventory & Demand")
            if not df_demand.empty:
                col_a, col_b = st.columns(2)
                with col_a:
                    fig_inv = px.bar(df_demand, x="product_id", y="current_stock", title="Current Stock by Product")
                    st.plotly_chart(fig_inv, use_container_width=True)
                with col_b:
                    fig_scat = px.scatter(df_demand, x="avg_daily_sales", y="predicted_demand", title="Avg vs Predicted Demand", hover_data=["product_id"])
                    max_val = max(df_demand["avg_daily_sales"].max(), df_demand["predicted_demand"].max())
                    fig_scat.add_shape(type="line", x0=0, y0=0, x1=max_val, y1=max_val, line=dict(color="grey", dash="dash"))
                    st.plotly_chart(fig_scat, use_container_width=True)
                if df_demand.get("demand_spike", pd.Series(False)).any():
                    st.warning("⚠️ Demand Spikes Detected!")
                st.dataframe(df_demand, use_container_width=True)

        with tab3:
            st.subheader("Reorder Alerts")
            if not df_reorder.empty:
                risky = df_reorder[df_reorder["stockout_risk"]]
                for _, row in risky.iterrows():
                    color = "red" if row["days_until_stockout"] < 3 else "orange"
                    st.markdown(f"<div style='border: 2px solid {color}; padding: 10px; margin: 5px; border-radius: 5px;'>{row['alert_message']}</div>", unsafe_allow_html=True)
                fig_reorder = px.bar(df_reorder, x="product_id", y="reorder_quantity", color="days_until_stockout", title="Reorder Quantities")
                st.plotly_chart(fig_reorder, use_container_width=True)
                st.dataframe(df_reorder, use_container_width=True)

        with tab4:
            st.subheader("Suppliers")
            if not df_sup.empty:
                fig_sup = px.bar(df_sup, y="supplier_id", x="reliability_score", orientation='h', title="Supplier Reliability")
                fig_sup.add_vline(x=85, line_dash="dash", line_color="green")
                fig_sup.add_vline(x=60, line_dash="dash", line_color="orange")
                st.plotly_chart(fig_sup, use_container_width=True)
                fig_scat2 = px.scatter(df_sup, x="average_delay", y="reliability_score", size="total_shipments", hover_data=["supplier_id"])
                st.plotly_chart(fig_scat2, use_container_width=True)
                st.dataframe(df_sup, use_container_width=True)

        with tab5:
            st.subheader("Warehouses")
            if not df_ware.empty:
                for _, row in df_ware.iterrows():
                    st.markdown(f"**{row['warehouse_id']}** Capacity: {row['total_stock']} / {row['capacity']}")
                    pct = min(1.0, row['utilization_percent']/100)
                    st.progress(pct)
                st.dataframe(df_ware, use_container_width=True)

        with tab6:
            st.subheader("Cost Analysis")
            if not df_cost.empty:
                col_a, col_b, col_c = st.columns(3)
                col_a.metric("Total Holding Cost", f"${df_cost['inventory_holding_cost'].sum():,.2f}")
                col_b.metric("Total Stockout Risk", f"${df_cost['stockout_cost'].sum():,.2f}")
                col_c.metric("Total Exposure", f"${df_cost['total_cost_impact'].sum():,.2f}")
                
                fig_tree = px.treemap(df_cost, path=[px.Constant("All"), "product_id"], values="total_cost_impact", title="Cost Impact Treemap")
                st.plotly_chart(fig_tree, use_container_width=True)
                fig_stack = px.bar(df_cost, x="product_id", y=["inventory_holding_cost", "stockout_cost"], title="Holding vs Stockout Cost")
                st.plotly_chart(fig_stack, use_container_width=True)
                st.dataframe(df_cost, use_container_width=True)

        with tab7:
            st.subheader("Raw Data Explorer")
            all_files = staged_files + os.listdir(PROCESSED_DIR)
            all_files = [f for f in all_files if f.endswith(('.csv', '.xlsx', '.json'))]
            if all_files:
                selected_file = st.selectbox("Select file to preview", all_files)
                fpath = os.path.join(workspace_dir, selected_file)
                if not os.path.exists(fpath):
                    fpath = os.path.join(PROCESSED_DIR, selected_file)
                
                try:
                    df_preview = pd.read_csv(fpath) if fpath.endswith('.csv') else (pd.read_excel(fpath) if fpath.endswith('.xlsx') else pd.read_json(fpath))
                    st.write(f"**Rows:** {df_preview.shape[0]} | **Columns:** {df_preview.shape[1]}")
                    
                    schema_df = pd.DataFrame({
                        "Column": df_preview.columns,
                        "Type": df_preview.dtypes.astype(str),
                        "Nulls": df_preview.isnull().sum(),
                        "Null %": (df_preview.isnull().sum() / len(df_preview) * 100).round(1),
                        "Sample": df_preview.iloc[0].astype(str) if not df_preview.empty else ""
                    })
                    st.dataframe(schema_df, use_container_width=True)
                    
                    st.write("Instant Chart")
                    num_cols = df_preview.select_dtypes(include=np.number).columns.tolist()
                    cat_cols = df_preview.select_dtypes(exclude=np.number).columns.tolist()
                    if num_cols:
                        c1, c2 = st.columns(2)
                        y_col = c1.selectbox("Y-axis (Numeric)", num_cols)
                        x_col = c2.selectbox("X-axis (Category)", cat_cols if cat_cols else df_preview.columns)
                        st.plotly_chart(px.bar(df_preview, x=x_col, y=y_col), use_container_width=True)
                    
                    st.dataframe(df_preview, use_container_width=True)
                    
                    st.markdown("### 🛡️ Data Quality Monitor")
                    # Schema Validation
                    st.write("**Schema Validation**")
                    expected_cols = {
                        "inventory": ["product_id", "current_stock", "safety_stock"],
                        "sales": ["product_id", "daily_sales"],
                        "suppliers": ["supplier_id", "lead_time_days"],
                        "shipments": ["shipment_id", "supplier_id", "product_id"],
                        "warehouses": ["warehouse_id", "capacity"]
                    }
                    dtype = next((k for k,v in expected_cols.items() if all(c in df_preview.columns for c in v)), None)
                    if dtype:
                        st.success(f"✅ Matches expected schema for: {dtype}")
                    else:
                        st.warning("❌ Unrecognized or generic schema")
                        
                    # Duplicates & Ranges
                    dups = df_preview.duplicated().sum()
                    st.write(f"**Duplicate Rows:** {dups} " + ("🔴" if dups > 0 else "🟢"))
                    
                    issues = []
                    for col in df_preview.select_dtypes(include=np.number).columns:
                        if (df_preview[col] < 0).any(): issues.append(f"🔴 `{col}` contains negative values!")
                        if "delay" in col and (df_preview[col] > 365).any(): issues.append(f"🔴 `{col}` contains values > 365!")
                    for i in issues: st.write(i)
                    
                    # Auto-suggest
                    st.write("**Auto-Suggest Fixes**")
                    nulls = df_preview.isnull().sum()
                    for col, count in nulls.items():
                        if count > 0:
                            st.info(f"💡 Column `{col}` has {count} nulls — recommend fill with {'0' if df_preview[col].dtype in [np.float64, np.int64] else 'UNKNOWN'}")
                    
                    # Score
                    score = max(0, 100 - (dups/max(1, len(df_preview))*50) - (nulls.sum()/(df_preview.size or 1)*50) - (len(issues)*5))
                    fig_g = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=score,
                        title={'text': "Data Quality Score"},
                        gauge={'axis': {'range': [0, 100]},
                               'bar': {'color': "green" if score > 80 else "orange" if score > 50 else "red"}}
                    ))
                    st.plotly_chart(fig_g, use_container_width=True)
                except Exception as e:
                    st.error(f"Error reading {selected_file}: {e}")

data_lab_page()
