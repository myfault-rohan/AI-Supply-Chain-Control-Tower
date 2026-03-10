import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import os
import sys
from streamlit_autorefresh import st_autorefresh

# Add project root to path for imports
import sys
import os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from alerts.ai_supply_chain_advisor import ask_supply_chain_question
from risk_engine.simulation_engine import simulate_supply_chain

from backend.auth import authenticate

# Authentication logic
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None

if not st.session_state.logged_in:
    st.set_page_config(page_title="Supply Chain Login", page_icon="🔑")
    st.title("🔐 AI Supply Chain Control Tower Login")
    
    with st.container():
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Login"):
            if authenticate(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.rerun()
            else:
                st.error("Invalid credentials")
    st.stop()

# Page configuration
st.set_page_config(
    page_title="Supply Chain Control Tower",
    page_icon="📡",
    layout="wide"
)

# Configuration
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

# --- API Fetching Functions ---

def get_live_data():
    """Fetch live streaming inventory data from the backend"""
    try:
        response = requests.get(f"{API_URL}/live_inventory")
        if response.status_code == 200:
            return pd.DataFrame(response.json())
        else:
            st.error("API returned an error.")
            return None
    except Exception as e:
        st.error(f"Error connecting to API: {e}")
        return None

def get_inventory():
    """Fetch current inventory status from the backend"""
    try:
        response = requests.get(f"{API_URL}/inventory")
        response.raise_for_status()
        return pd.DataFrame(response.json())
    except Exception as e:
        st.error(f"Error fetching inventory: {e}")
        return pd.DataFrame()

def get_demand_forecast():
    """Fetch demand forecast data from the backend"""
    try:
        response = requests.get(f"{API_URL}/demand_forecast")
        response.raise_for_status()
        return pd.DataFrame(response.json())
    except Exception as e:
        st.error(f"Error fetching demand forecast: {e}")
        return pd.DataFrame()

def get_reorder_recommendations():
    """Fetch reorder recommendations from the backend"""
    try:
        response = requests.get(f"{API_URL}/reorder_recommendations")
        response.raise_for_status()
        return pd.DataFrame(response.json())
    except Exception as e:
        st.error(f"Error fetching reorder recommendations: {e}")
        return pd.DataFrame()

def get_alerts():
    """Fetch supply chain alerts from the backend"""
    try:
        response = requests.get(f"{API_URL}/alerts")
        response.raise_for_status()
        return pd.DataFrame(response.json())
    except Exception as e:
        st.error(f"Error fetching alerts: {e}")
        return pd.DataFrame()

def get_health():
    """Fetch supply chain health data from the backend"""
    try:
        response = requests.get(f"{API_URL}/health")
        response.raise_for_status()
        return pd.DataFrame(response.json())
    except Exception as e:
        st.error(f"Error fetching health data: {e}")
        return pd.DataFrame()

def get_supplier_performance():
    """Fetch supplier performance metrics from the backend"""
    try:
        response = requests.get(f"{API_URL}/supplier_performance")
        response.raise_for_status()
        return pd.DataFrame(response.json())
    except Exception as e:
        st.error(f"Error fetching supplier performance: {e}")
        return pd.DataFrame()

def get_warehouse_utilization():
    """Fetch warehouse utilization metrics from the backend"""
    try:
        response = requests.get(f"{API_URL}/warehouse_utilization")
        response.raise_for_status()
        return pd.DataFrame(response.json())
    except Exception as e:
        st.error(f"Error fetching warehouse utilization: {e}")
        return pd.DataFrame()

def get_global_risk_summary():
    """Fetch global risk summary from the backend"""
    try:
        response = requests.get(f"{API_URL}/global_risk_summary")
        response.raise_for_status()
        return pd.DataFrame(response.json())
    except Exception as e:
        st.error(f"Error fetching global risk summary: {e}")
        return pd.DataFrame()

def get_daily_report():
    """Fetch daily risk report from the backend"""
    try:
        response = requests.get(f"{API_URL}/daily_report")
        response.raise_for_status()
        return pd.DataFrame(response.json())
    except Exception as e:
        st.error(f"Error fetching daily report: {e}")
        return pd.DataFrame()

def get_cost_analysis():
    """Fetch supply chain cost analysis from the backend"""
    try:
        response = requests.get(f"{API_URL}/cost_analysis")
        response.raise_for_status()
        return pd.DataFrame(response.json())
    except Exception as e:
        st.error(f"Error fetching cost analysis: {e}")
        return pd.DataFrame()

# --- Dashboard Layout ---

def main():
    st.title("📡 AI Supply Chain Control Tower (API-Driven)")
    st.markdown("---")

    # --- Global Supply Chain Risk Overview ---
    st.header("🌍 Global Supply Chain Risk Overview")
    risk_summary = get_global_risk_summary()
    
    if not risk_summary.empty:
        col_risk1, col_risk2, col_risk3, col_risk4 = st.columns(4)
        
        with col_risk1:
            st.metric("Critical Products", risk_summary["critical_products"][0], delta_color="inverse")
        with col_risk2:
            st.metric("Unreliable Suppliers", risk_summary["unreliable_suppliers"][0], delta_color="inverse")
        with col_risk3:
            st.metric("Overloaded Warehouses", risk_summary["overloaded_warehouses"][0], delta_color="inverse")
        with col_risk4:
            st.metric("High Cost Impact Products", risk_summary["high_cost_products"][0], delta_color="inverse")
    else:
        st.info("Risk summary not available")

    st.markdown("---")

    # --- AI Supply Chain Advisor ---
    st.header("🤖 AI Supply Chain Advisor")
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # React to user input
    if prompt := st.chat_input("Ask me about stockouts, demand, or reorders..."):
        # Display user message in chat message container
        with st.chat_message("user"):
            st.markdown(prompt)
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Generate response
        response = ask_supply_chain_question(prompt)
        
        # Display assistant response in chat message container
        with st.chat_message("assistant"):
            st.markdown(response)
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})

    st.markdown("---")

    # --- Upload Supply Chain Data ---
    st.header("📤 Upload Supply Chain Data")

    uploaded_file = st.file_uploader(
        "Upload CSV file (inventory, sales, suppliers)", type="csv"
    )

    if uploaded_file is not None:
        try:
            with st.spinner("Uploading file..."):
                response = requests.post(
                    f"{API_URL}/upload_data",
                    params={"username": st.session_state.username},
                    files={"file": uploaded_file}
                )

                if response.status_code == 200:
                    st.success("File uploaded successfully")
                else:
                    st.error(f"Upload failed: {response.text}")

        except Exception as e:
            st.error(f"Error uploading file: {e}")

    st.markdown("---")

    # Sidebar for control
    st.sidebar.header("Dashboard Control")
    if st.sidebar.button("🔄 Refresh Data"):
        st.rerun()
    
    st.sidebar.markdown(f"**Backend Status:** Connected to {API_URL}")

    # --- Supply Chain Scenario Simulator ---
    st.header("📈 Supply Chain Scenario Simulator")
    st.markdown("Stress-test your supply chain by simulating demand spikes and delivery delays.")
    
    col_sim1, col_sim2 = st.columns(2)
    with col_sim1:
        demand_spike = st.slider("Demand Increase Percentage (%)", 0, 100, 25)
    with col_sim2:
        delay_days = st.number_input("Supplier Delay (Days)", 0, 30, 2)
        
    if st.button("🚀 Run Simulation"):
        with st.spinner("Simulating scenario..."):
            results = simulate_supply_chain(demand_spike, delay_days)
            
            if results:
                st.subheader("Simulation Results")
                # Display metrics
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Critical Products", results['critical_products'], delta=results['critical_products'], delta_color="inverse")
                m2.metric("Warning Products", results['warning_products'], delta=results['warning_products'], delta_color="inverse")
                m3.metric("Good Products", results['good_products'])
                m4.metric("Total Reorder Qty", f"{results['total_reorder_quantity']:,}")
                
                # Pie chart
                health_data = pd.DataFrame({
                    "Category": ["CRITICAL", "WARNING", "GOOD"],
                    "Count": [results['critical_products'], results['warning_products'], results['good_products']]
                })
                
                # Filter out zero categories for a cleaner pie chart
                health_data = health_data[health_data['Count'] > 0]
                
                if not health_data.empty:
                    fig_sim = px.pie(
                        health_data, 
                        values='Count', 
                        names='Category',
                        title=f"Simulated Health Distribution ({demand_spike}% Demand, {delay_days}d Delay)",
                        color='Category',
                        color_discrete_map={'GOOD': '#28a745', 'WARNING': '#ffc107', 'CRITICAL': '#dc3545'},
                        hole=0.4
                    )
                    st.plotly_chart(fig_sim, use_container_width=True)
                else:
                    st.info("No products to display in health chart.")
            else:
                st.error("Simulation failed. Ensure supply_chain_health.csv and reorder_recommendations.csv exist.")

    st.markdown("---")

    # --- Live Supply Chain Monitor ---
    st.header("📊 Live Supply Chain Monitor")
    
    # Auto refresh every 5 seconds
    st_autorefresh(interval=5000, key="data_refresh")

    data = get_live_data()

    if data is not None and not data.empty:
        st.dataframe(data)

        st.subheader("📈 Live Stock Levels")
        st.bar_chart(data["current_stock"])
    else:
        st.warning("No live inventory data available.")

    st.markdown("---")

    # --- 1. Inventory Overview ---
    st.header("📦 Inventory Overview")
    inventory_df = get_inventory()
    if not inventory_df.empty:
        st.dataframe(inventory_df, width='stretch')
    else:
        st.warning("No inventory data available.")

    st.markdown("---")

    # --- Supply Chain Health Monitor ---
    st.header("🌡️ Supply Chain Health Monitor")
    health_df = get_health()
    if not health_df.empty:
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.subheader("Health Distribution")
            health_counts = health_df['health_status'].value_counts().reset_index()
            health_counts.columns = ['Status', 'Count']
            
            # Map colors for the chart
            color_map = {'GOOD': '#28a745', 'WARNING': '#ffc107', 'CRITICAL': '#dc3545'}
            
            fig_health = px.bar(
                health_counts, 
                x='Status', 
                y='Count', 
                color='Status',
                color_discrete_map=color_map,
                title="Products by Health Category"
            )
            st.plotly_chart(fig_health, width='stretch')
            
        with col_right:
            st.subheader("Health Indicators Table")
            
            # Formatting function for colors
            def style_health(val):
                color = 'green' if val == 'GOOD' else 'orange' if val == 'WARNING' else 'red'
                return f'color: {color}; font-weight: bold'
            
            display_columns = ['product_id', 'current_stock', 'days_until_stockout', 'health_status']
            st.dataframe(
                health_df[display_columns].style.map(style_health, subset=['health_status']),
                width='stretch'
            )
    else:
        st.warning("No health data available. Please run the health score engine.")

    st.markdown("---")

    # --- 2. Demand Forecast Chart ---
    st.header("📈 Demand Forecast Chart")
    forecast_df = get_demand_forecast()
    if not forecast_df.empty:
        # Sort by predicted demand for visualization
        sorted_forecast = forecast_df.sort_values(by='predicted_demand', ascending=False).head(15)
        fig = px.bar(
            sorted_forecast,
            x='product_id',
            y='predicted_demand',
            color='predicted_demand',
            labels={'predicted_demand': 'Predicted Demand', 'product_id': 'Product ID'},
            title="Top 15 Products by Predicted Demand",
            color_continuous_scale="Viridis"
        )
        st.plotly_chart(fig, width='stretch')
    else:
        st.warning("No forecast data available.")

    st.markdown("---")

    # --- 3. Reorder Recommendations ---
    st.header("📋 Reorder Recommendations")
    reorder_df = get_reorder_recommendations()
    if not reorder_df.empty:
        # Filter for products that actually need reordering
        actual_reorders = reorder_df[reorder_df['reorder_quantity'] > 0]
        if not actual_reorders.empty:
            st.dataframe(actual_reorders[['product_id', 'reorder_quantity', 'supplier_lead_time', 'alert_message']], width='stretch')
        else:
            st.success("All stock levels are currently healthy. No reorders needed.")
    else:
        st.warning("No reorder recommendation data available.")

    st.markdown("---")

    # --- 4. Risk Alerts ---
    st.header("⚠️ Risk Alerts")
    alerts_df = get_alerts()
    if not alerts_df.empty:
        st.subheader("Critical Stockout Risks")
        for _, row in alerts_df.iterrows():
            st.error(row['alert_message'])
    else:
        st.success("No critical stockout alerts at this time.")

    st.markdown("---")

    # --- 5. Supplier Performance ---
    st.header("🚚 Supplier Performance")
    
    supplier_df = get_supplier_performance()
    if not supplier_df.empty:
        st.dataframe(supplier_df, width='stretch')
        
        st.subheader("Reliability Scores by Supplier")
        # Ensure supplier_id is the index for a better bar chart
        chart_data = supplier_df.set_index('supplier_id')['reliability_score']
        st.bar_chart(chart_data)
    else:
        st.info("No supplier performance data available")

    st.markdown("---")

    # --- 6. Warehouse Utilization ---
    st.header("🏭 Warehouse Utilization")
    
    wh_df = get_warehouse_utilization()
    if not wh_df.empty:
        st.dataframe(wh_df, width='stretch')
        
        st.subheader("Utilization Percentage by Warehouse")
        # Ensure warehouse_id is the index for a better bar chart
        wh_chart_data = wh_df.set_index('warehouse_id')['utilization_percent']
        st.bar_chart(wh_chart_data)
    else:
        st.info("No warehouse utilization data available")

    st.markdown("---")

    # --- 7. Supply Chain Cost Analytics ---
    st.header("💰 Supply Chain Cost Analytics")
    
    cost_df = get_cost_analysis()
    if not cost_df.empty:
        st.dataframe(cost_df, width='stretch')
        
        st.subheader("Total Cost Impact by Product")
        # Sort by total impact for better visualization
        top_costs = cost_df.sort_values(by='total_cost_impact', ascending=False).head(20)
        st.bar_chart(top_costs.set_index('product_id')['total_cost_impact'])
    else:
        st.info("No cost analysis data available")

    st.markdown("---")

    # --- 8. Daily Risk Report ---
    st.header("📄 Daily Risk Report")
    
    report_df = get_daily_report()
    if not report_df.empty:
        st.dataframe(report_df, width='stretch')
        
        csv = report_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Daily Report (CSV)",
            data=csv,
            file_name=f"daily_supply_chain_report_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )
    else:
        st.info("No daily report available")

    # Footer
    st.markdown("---")
    st.caption("Powered by FastAPI & Streamlit")

    # --- AI Supply Chain Advisor (Simple Version) ---
    st.header("🤖 AI Supply Chain Advisor")

    user_question = st.text_input("Ask a supply chain question", key="advisor_input")

    if user_question:

        response = ask_supply_chain_question(user_question)

        st.write(response)

if __name__ == "__main__":
    main()
