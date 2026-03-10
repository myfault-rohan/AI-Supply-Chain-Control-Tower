import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import requests

# Page configuration
st.set_page_config(
    page_title="AI Supply Chain Control Tower",
    page_icon="🏗️",
    layout="wide"
)

# Custom Styling
st.markdown("""
<style>
    .main {
        background-color: #f5f7f9;
    }
    .metric-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# File Paths
DEMAND_FILE = 'dataset/demand_predictions.csv'
REORDER_FILE = 'dataset/reorder_recommendations.csv'

def load_data():
    """Load datasets for the dashboard"""
    if not os.path.exists(DEMAND_FILE) or not os.path.exists(REORDER_FILE):
        return None, None
    
    demand_df = pd.read_csv(DEMAND_FILE)
    reorder_df = pd.read_csv(REORDER_FILE)
    return demand_df, reorder_df

def main():
    st.title("🏗️ AI Supply Chain Control Tower")
    st.markdown("---")

    demand_df, reorder_df = load_data()

    if demand_df is None or reorder_df is None:
        st.error("Data files not found. Please run the processing and ML pipelines first.")
        st.info("Required files: `dataset/demand_predictions.csv` and `dataset/reorder_recommendations.csv`.")
        return

    # --- 1. Global Metrics ---
    st.subheader("📊 Global Supply Chain Metrics")
    col1, col2, col3, col4 = st.columns(4)

    total_products = demand_df['product_id'].nunique()
    at_risk_count = reorder_df[reorder_df['stockout_risk'] == True]['product_id'].nunique()
    avg_inv_days = demand_df['inventory_days'].mean()
    total_reorder_qty = reorder_df['reorder_quantity'].sum()

    with col1:
        st.metric("Total Products", total_products)
    with col2:
        st.metric("Products at Risk", at_risk_count, delta=at_risk_count, delta_color="inverse")
    with col3:
        st.metric("Avg Inventory Days", f"{avg_inv_days:.1f}")
    with col4:
        st.metric("Total Reorder Qty", int(total_reorder_qty))

    st.markdown("---")

    # --- Real-Time Alerts ---
    st.header("🚨 Real-Time Alerts")

    try:
        response = requests.get("http://127.0.0.1:8000/live_alerts")
        alerts = response.json()

        if alerts:
            df_alerts = pd.DataFrame(alerts)
            st.dataframe(df_alerts, use_container_width=True)
        else:
            st.success("No critical alerts detected")

    except Exception:
        st.error("Could not fetch alerts")

    st.markdown("---")

    # --- 2. Demand Forecast Chart & 5. Inventory Visualization ---
    left_col, right_col = st.columns(2)

    with left_col:
        st.subheader("📈 Demand Forecast (Next 30 Days)")
        # Sort by predicted demand for better visualization
        forecast_chart_df = demand_df.sort_values(by='predicted_demand', ascending=False).head(15)
        fig_demand = px.bar(
            forecast_chart_df,
            x='product_id',
            y='predicted_demand',
            color='predicted_demand',
            labels={'predicted_demand': 'Predicted Daily Sales', 'product_id': 'Product ID'},
            title="Top 15 Products by Predicted Demand",
            color_continuous_scale='Viridis'
        )
        st.plotly_chart(fig_demand, width='stretch')

    with right_col:
        st.subheader("📦 Inventory Levels by Warehouse")
        warehouse_inv = demand_df.groupby('warehouse_id')['current_stock'].sum().reset_index()
        fig_inv = px.pie(
            warehouse_inv,
            values='current_stock',
            names='warehouse_id',
            title="Stock Distribution Across Warehouses",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        st.plotly_chart(fig_inv, width='stretch')

    st.markdown("---")

    # --- 3. Stockout Risk Table ---
    st.subheader("⚠️ High Stockout Risk Alert")
    risk_df = reorder_df[reorder_df['stockout_risk'] == True][
        ['product_id', 'current_stock', 'predicted_demand', 'days_until_stockout']
    ]
    
    if len(risk_df) > 0:
        st.dataframe(risk_df.style.background_gradient(subset=['days_until_stockout'], cmap='Reds_r'), width='stretch')
    else:
        st.success("No immediate stockout risks detected across the supply chain.")

    st.markdown("---")

    # --- 4. Reorder Recommendation Table ---
    st.subheader("📋 Reorder Recommendations")
    
    reorder_table = reorder_df[reorder_df['reorder_quantity'] > 0][
        ['product_id', 'reorder_quantity', 'alert_message']
    ]
    
    if len(reorder_table) > 0:
        st.table(reorder_table)
    else:
        st.info("Stock levels are currently healthy. No reorders required.")

    # Sidebar info
    st.sidebar.header("About")
    st.sidebar.info(
        "This Control Tower integrates PySpark for data processing, "
        "XGBoost for demand forecasting, and a heuristic Risk Engine "
        "for reorder optimization."
    )
    if st.sidebar.button("Refresh Data"):
        st.rerun()

if __name__ == "__main__":
    main()
