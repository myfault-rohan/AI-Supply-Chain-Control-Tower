import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os, sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dashboard.i18n import t
from risk_engine.simulation_engine import run_simulation, run_monte_carlo
from config import DATASET_DIR

st.title(f"{t('nav_sim_lab')} 🧪" if t("nav_sim_lab") != "nav_sim_lab" else "Simulation Lab 🧪")
st.markdown("Run crisis scenarios and Monte Carlo simulations to evaluate supply chain resilience.")

processed_dir = os.path.join(DATASET_DIR, "processed files")
health_file = os.path.join(processed_dir, "supply_chain_health.csv")
reorder_file = os.path.join(processed_dir, "reorder_recommendations.csv")

if not os.path.exists(health_file) or not os.path.exists(reorder_file):
    st.warning("Please run the Analysis Pipeline in Data Lab first.")
    st.stop()

df_health = pd.read_csv(health_file)
df_reorder = pd.read_csv(reorder_file)
df_health["product_id"] = df_health["product_id"].astype(str)
df_reorder["product_id"] = df_reorder["product_id"].astype(str)
cols_to_use = df_reorder.columns.difference(df_health.columns).tolist() + ['product_id']
df_base = df_health.merge(df_reorder[cols_to_use], on="product_id", how="left")

# Presets
st.markdown("### ⚡ Pre-built Scenarios")
sc1, sc2, sc3, sc4 = st.columns(4)

if "delay" not in st.session_state: st.session_state.delay = 0
if "spike" not in st.session_state: st.session_state.spike = 0
if "cap" not in st.session_state: st.session_state.cap = 100
if "cost" not in st.session_state: st.session_state.cost = 1.0

def apply_scenario(d, s, c, m):
    st.session_state.delay = d
    st.session_state.spike = s
    st.session_state.cap = c
    st.session_state.cost = m

if sc1.button("🚢 Port Disruption", use_container_width=True): apply_scenario(21, 0, 100, 1.0)
if sc2.button("📈 Demand Surge", use_container_width=True): apply_scenario(0, 150, 100, 1.0)
if sc3.button("🏭 Factory Shutdown", use_container_width=True): apply_scenario(0, 0, 0, 1.0)
if sc4.button("⚡ Energy Crisis", use_container_width=True): apply_scenario(0, 0, 100, 2.5)

st.markdown("---")

c1, c2, c3, c4 = st.columns(4)
d_val = c1.slider("Delay Days", 0, 60, st.session_state.delay)
s_val = c2.slider("Demand Spike (%)", -50, 300, st.session_state.spike)
c_val = c3.slider("Supplier Capacity (%)", 0, 100, st.session_state.cap)
m_val = c4.slider("Cost Multiplier", 0.5, 5.0, float(st.session_state.cost), 0.1)

st.session_state.delay = d_val
st.session_state.spike = s_val
st.session_state.cap = c_val
st.session_state.cost = m_val

df_sim = run_simulation(df_base, d_val, s_val, c_val, m_val)

st.markdown("### 📊 Scenario Impact")

diff_df = pd.DataFrame({
    "Product": df_base["product_id"].astype(str),
    "Before": df_base.get("days_until_stockout_x", df_base.get("days_until_stockout")),
    "After": df_sim["sim_days_until_stockout"]
}).melt(id_vars="Product", var_name="Scenario", value_name="Days Until Stockout")

fig_bar = px.bar(diff_df, x="Product", y="Days Until Stockout", color="Scenario", barmode="group",
                 title="Days Until Stockout (Before vs After)")
# Cap y axis to prevent huge bars
fig_bar.update_yaxes(range=[0, min(100, diff_df["Days Until Stockout"].max() + 5)])
st.plotly_chart(fig_bar, use_container_width=True)

total_cost = df_sim["sim_financial_impact"].sum() if "sim_financial_impact" in df_sim else 0
st.metric("Estimated Financial Impact (USD)", f"${total_cost:,.2f}", delta=f"${total_cost - df_base.get('current_stock', pd.Series([0])).sum()*2:,.2f} vs Base")

st.markdown("---")
st.markdown("### 🎲 Monte Carlo Risk Distribution (1000 Iterations)")
with st.spinner("Running Monte Carlo simulation..."):
    mc_results = run_monte_carlo(df_base, d_val, s_val, c_val, m_val, 1000)

fig_hist = px.histogram(pd.DataFrame({'Impact': mc_results}), x='Impact', nbins=50, title="Probability Distribution of Financial Impact")
fig_hist.update_layout(xaxis_title="Financial Impact ($)", yaxis_title="Frequency")
fig_hist.add_vline(x=np.percentile(mc_results, 95), line_dash="dash", line_color="red", annotation_text="95% Value at Risk")
st.plotly_chart(fig_hist, use_container_width=True)
