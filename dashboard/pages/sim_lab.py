import streamlit as st
import pandas as pd
import plotly.express as px
from risk_engine.simulation_engine import simulate_supply_chain
from dashboard.utils import fetch_data, no_data_view

st.title("🧪 Advanced Simulation Lab")
st.markdown("### Strategic Stress-Testing & Scenario Analysis")

# Check for required data
health_df = fetch_data("/health")

if health_df.empty:
    no_data_view("Scenario Simulation")
else:
    col_ctrl, col_viz = st.columns([1, 2])
    
    with col_ctrl:
        st.subheader("Control Parameters")
        demand_spike = st.slider("Demand Surge (%)", 0, 200, 50, help="Simulate a sudden spike in market demand.")
        delay_days = st.slider("Supply Chain Delay (Days)", 0, 60, 5, help="Simulate logistics or supplier production delays.")
        
        st.markdown("---")
        if st.button("🚀 Run Crisis Simulation"):
            with st.spinner("Processing scenario permutations..."):
                results = simulate_supply_chain(demand_spike, delay_days)
                if results:
                    st.session_state.sim_results = results
                    st.success("Simulation Complete.")
                else:
                    st.error("Simulation engine failed to initialize.")

    with col_viz:
        if "sim_results" in st.session_state:
            res = st.session_state.sim_results
            st.subheader("Simulated Impact Analysis")
            
            c1, c2 = st.columns(2)
            c1.metric("Critical Risks", res['critical_products'], delta=res['critical_products'], delta_color="inverse")
            c2.metric("Warnings", res['warning_products'], delta=res['warning_products'], delta_color="inverse")
            
            # Healthcare distribution chart
            sim_data = pd.DataFrame({
                "Category": ["CRITICAL", "WARNING", "GOOD"],
                "Count": [res['critical_products'], res['warning_products'], res['good_products']]
            })
            fig = px.pie(
                sim_data, values="Count", names="Category", 
                color="Category",
                color_discrete_map={'GOOD': '#00ff88', 'WARNING': '#ffcc00', 'CRITICAL': '#ff3300'},
                template="plotly_dark",
                title=f"Outcome: {demand_spike}% Demand / {delay_days}d Delay"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Configure your scenario parameters and click 'Run' to see the predicted impact.")
