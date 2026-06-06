"""
AI Supply Chain Control Tower — Dashboard
==========================================
Beautiful 5-tab Streamlit dashboard. No login required.
Run: streamlit run dashboard/app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os, json
from pathlib import Path

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Supply Chain Control Tower",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

ROOT       = Path(__file__).parent.parent
MODELS_DIR = ROOT / "data" / "models"
RAW_DIR    = ROOT / "data" / "raw"
PROC_DIR   = ROOT / "data" / "processed"

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  .stApp { background: #0a0e1a; }

  /* Metric cards */
  [data-testid="metric-container"] {
    background: linear-gradient(135deg, #141829 0%, #1a1f35 100%);
    border: 1px solid #2a3050;
    border-radius: 12px;
    padding: 16px !important;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    transition: transform 0.2s;
  }
  [data-testid="metric-container"]:hover { transform: translateY(-2px); }

  [data-testid="stMetricLabel"] { color: #8892b0 !important; font-size: 0.78rem !important; letter-spacing: 0.05em; }
  [data-testid="stMetricValue"] { color: #ccd6f6 !important; font-size: 1.8rem !important; font-weight: 700; }
  [data-testid="stMetricDelta"] { font-size: 0.82rem !important; }

  /* Sidebar */
  [data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1117 0%, #141829 100%);
    border-right: 1px solid #21262d;
  }

  /* Tab styling */
  .stTabs [data-baseweb="tab-list"] { gap: 4px; background: #141829; border-radius: 10px; padding: 4px; }
  .stTabs [data-baseweb="tab"] {
    background: transparent;
    border-radius: 8px;
    color: #8892b0;
    font-weight: 500;
    padding: 8px 16px;
  }
  .stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #1e3a5f, #0f2744) !important;
    color: #64b5f6 !important;
    box-shadow: 0 2px 8px rgba(100,181,246,0.2);
  }

  /* Headers */
  h1 { color: #ccd6f6 !important; font-weight: 700 !important; }
  h2, h3 { color: #a8b2d8 !important; }

  /* Section divider */
  .section-header {
    font-size: 0.72rem;
    font-weight: 600;
    color: #64b5f6;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin: 12px 0 4px 0;
    padding-left: 4px;
  }

  /* Insight cards */
  .insight-card {
    background: linear-gradient(135deg, #141829, #1a1f35);
    border-left: 3px solid #64b5f6;
    border-radius: 0 8px 8px 0;
    padding: 12px 16px;
    margin: 6px 0;
    font-size: 0.88rem;
    color: #a8b2d8;
  }
  .insight-card.warning { border-left-color: #ffb347; }
  .insight-card.critical { border-left-color: #ff6b6b; }
  .insight-card.success { border-left-color: #4caf50; }
</style>
""", unsafe_allow_html=True)


# ── Data Loaders (cached) ─────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_json(path):
    try:
        with open(path) as f: return json.load(f)
    except Exception: return {}

@st.cache_data(ttl=300)
def load_csv(path):
    try: return pd.read_csv(path)
    except Exception: return pd.DataFrame()

def pipeline_ran():
    return (MODELS_DIR / "demand_metrics.json").exists()


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏭 Control Tower")
    st.markdown("---")

    if pipeline_ran():
        dm = load_json(MODELS_DIR / "demand_metrics.json")
        sm = load_json(MODELS_DIR / "supplier_risk_metrics.json")
        im = load_json(MODELS_DIR / "inventory_metrics.json")
        am = load_json(MODELS_DIR / "anomaly_metrics.json")

        st.markdown('<div class="section-header">Model Health</div>', unsafe_allow_html=True)
        st.metric("Demand R²",   f"{dm.get('cv_r2', 0):.3f}")
        st.metric("Supplier R²", f"{sm.get('r2', 0):.3f}")
        st.metric("Anomaly Rate", f"{am.get('anomaly_rate', 0):.1f}%")
        st.metric("Cost Savings", f"${im.get('total_savings', 0):,.0f}")
        st.markdown("---")
        st.success("✅ Pipeline Ready")
    else:
        st.warning("⚠️ Run pipeline first:\n```\npython run.py --mode all\n```")

    st.markdown("---")
    st.markdown('<div class="section-header">Quick Links</div>', unsafe_allow_html=True)
    st.markdown("📓 [Notebooks](../notebooks/)")
    st.markdown("📊 [MLflow UI](http://localhost:5000)")
    st.markdown("📁 [Raw Data](../data/raw/)")


# ── Main Header ───────────────────────────────────────────────────────────────
st.markdown("# 🏭 AI Supply Chain Control Tower")
st.markdown("*Real-time analytics · ML forecasting · Inventory optimization · Risk intelligence*")
st.markdown("---")

if not pipeline_ran():
    st.info("🚀 **Pipeline not yet run.** Execute `python run.py --mode all` to generate data and train models, then refresh this page.")
    st.stop()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Overview",
    "📈 Demand Forecast",
    "🚨 Anomaly Detection",
    "🚢 Supplier Risk",
    "📦 Inventory & Optimization",
])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    dm = load_json(MODELS_DIR / "demand_metrics.json")
    sm = load_json(MODELS_DIR / "supplier_risk_metrics.json")
    im = load_json(MODELS_DIR / "inventory_metrics.json")
    am = load_json(MODELS_DIR / "anomaly_metrics.json")

    st.markdown("### 🎯 Platform KPIs")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Demand Forecast R²",      f"{dm.get('cv_r2', 0):.3f}",   delta="Walk-forward CV")
    c2.metric("High-Risk Suppliers",      f"{sm.get('high_risk_suppliers', 0)}",
              delta=f"of {sm.get('n_suppliers', 0)} total", delta_color="inverse")
    c3.metric("Inventory Cost Savings",   f"${im.get('total_savings', 0):,.0f}",
              delta=f"{im.get('savings_pct', 0):.1f}% reduction")
    c4.metric("Anomalies Detected",       f"{am.get('total_anomalies', 0):,}",
              delta=f"{am.get('anomaly_rate', 0):.1f}% rate", delta_color="inverse")
    c5.metric("High-Risk Products",       f"{am.get('high_risk_products', 0)}",
              delta="anomaly ensemble", delta_color="inverse")

    st.markdown("---")

    # Sales trend
    col_l, col_r = st.columns([2, 1])
    with col_l:
        st.markdown("### 📈 Demand Forecasts vs Actuals")
        forecasts = load_csv(MODELS_DIR / "demand_forecasts.csv")
        if not forecasts.empty:
            fig = px.scatter(
                forecasts.sample(min(500, len(forecasts))),
                x="avg_actual_demand", y="avg_predicted_demand",
                color="forecast_accuracy",
                color_continuous_scale="Viridis",
                labels={"avg_actual_demand": "Actual Demand", "avg_predicted_demand": "Predicted Demand"},
                title="Actual vs Predicted Demand (per product)",
                template="plotly_dark",
            )
            # Perfect prediction line
            max_val = max(forecasts["avg_actual_demand"].max(), forecasts["avg_predicted_demand"].max())
            fig.add_shape(type="line", x0=0, y0=0, x1=max_val, y1=max_val,
                          line=dict(color="#64b5f6", width=1, dash="dash"))
            fig.update_layout(height=380, paper_bgcolor="#141829", plot_bgcolor="#0a0e1a")
            st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.markdown("### 🔑 Key Insights")
        st.markdown(f"""
        <div class="insight-card success">
            💡 Demand model achieves <b>{dm.get('avg_forecast_accuracy', 0):.1%}</b> accuracy
            across {dm.get('n_products', 0)} SKUs
        </div>
        <div class="insight-card warning">
            ⚠️ <b>{sm.get('high_risk_suppliers', 0)}</b> suppliers classified HIGH risk
            — review immediately
        </div>
        <div class="insight-card success">
            💰 EOQ optimization saves <b>${im.get('total_savings', 0):,.0f}</b>/year
            ({im.get('savings_pct', 0):.1f}% reduction)
        </div>
        <div class="insight-card critical">
            🚨 <b>{am.get('high_risk_products', 0)}</b> products show persistent
            anomalous demand patterns
        </div>
        """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — DEMAND FORECASTING
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### 📈 Demand Forecasting Results")

    dm = load_json(MODELS_DIR / "demand_metrics.json")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("CV MAE",  f"{dm.get('cv_mae', 0):.3f}")
    c2.metric("CV RMSE", f"{dm.get('cv_rmse', 0):.3f}")
    c3.metric("CV R²",   f"{dm.get('cv_r2', 0):.4f}")
    c4.metric("Products", f"{dm.get('n_products', 0)}")

    col_l, col_r = st.columns(2)

    with col_l:
        shap_df = load_csv(MODELS_DIR / "demand_shap_importance.csv")
        if not shap_df.empty:
            fig = px.bar(
                shap_df.head(10),
                x="mean_abs_shap", y="feature",
                orientation="h",
                color="mean_abs_shap",
                color_continuous_scale="Blues",
                title="SHAP Feature Importance — Demand Model",
                template="plotly_dark",
            )
            fig.update_layout(height=380, paper_bgcolor="#141829", plot_bgcolor="#0a0e1a",
                              yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig, use_container_width=True)

    with col_r:
        ts_df = load_csv(MODELS_DIR / "time_series_forecasts.csv")
        if not ts_df.empty:
            ts_df["date"] = pd.to_datetime(ts_df["date"])
            product = st.selectbox("Select Product", ts_df["product_id"].unique())
            prod_df = ts_df[ts_df["product_id"] == product]

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=prod_df["date"], y=prod_df["actual"],
                                     name="Actual", line=dict(color="#64b5f6", width=2)))
            fig.add_trace(go.Scatter(x=prod_df["date"], y=prod_df["forecast"],
                                     name="SARIMAX Forecast",
                                     line=dict(color="#ff9f40", width=2, dash="dot")))
            fig.update_layout(title=f"SARIMAX 30-Day Forecast — {product}",
                              template="plotly_dark", height=380,
                              paper_bgcolor="#141829", plot_bgcolor="#0a0e1a")
            st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — ANOMALY DETECTION
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### 🚨 Ensemble Anomaly Detection")

    am = load_json(MODELS_DIR / "anomaly_metrics.json")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Anomalies",    f"{am.get('total_anomalies', 0):,}")
    c2.metric("Anomaly Rate",       f"{am.get('anomaly_rate', 0):.1f}%")
    c3.metric("High-Risk Products", f"{am.get('high_risk_products', 0)}")
    c4.metric("Ensemble Strategy",  "2/3 Majority Vote")

    prod_summary = load_csv(MODELS_DIR / "anomaly_product_summary.csv")
    anomaly_res  = load_csv(MODELS_DIR / "anomaly_results.csv")

    col_l, col_r = st.columns(2)

    with col_l:
        if not prod_summary.empty:
            top_anomalous = prod_summary.nlargest(15, "anomaly_rate")
            fig = px.bar(
                top_anomalous,
                x="product_id", y="anomaly_rate",
                color="anomaly_rate",
                color_continuous_scale="Reds",
                title="Top 15 Products by Anomaly Rate",
                template="plotly_dark",
            )
            fig.update_layout(height=380, paper_bgcolor="#141829", plot_bgcolor="#0a0e1a")
            st.plotly_chart(fig, use_container_width=True)

    with col_r:
        if not anomaly_res.empty:
            anomaly_res["date"] = pd.to_datetime(anomaly_res["date"])
            cat_anom = anomaly_res.groupby(["date", "category"])["anomaly_label"].mean().reset_index()
            cat_anom["date"] = pd.to_datetime(cat_anom["date"])
            # Monthly aggregation
            cat_anom["month"] = cat_anom["date"].dt.to_period("M").astype(str)
            monthly = cat_anom.groupby(["month", "category"])["anomaly_label"].mean().reset_index()

            fig = px.line(
                monthly, x="month", y="anomaly_label",
                color="category",
                title="Monthly Anomaly Rate by Category",
                template="plotly_dark",
            )
            fig.update_layout(height=380, paper_bgcolor="#141829", plot_bgcolor="#0a0e1a",
                              xaxis_tickangle=45)
            st.plotly_chart(fig, use_container_width=True)

    # Detector agreement
    if not anomaly_res.empty:
        st.markdown("### 🔬 Detector Agreement Analysis")
        agree_cols = ["ecod_flag", "iforest_flag", "lof_flag"]
        agree_counts = {
            "All 3 agree (anomaly)": int(((anomaly_res[agree_cols].sum(axis=1)) == 3).sum()),
            "2 of 3 agree":          int(((anomaly_res[agree_cols].sum(axis=1)) == 2).sum()),
            "1 of 3 flags":          int(((anomaly_res[agree_cols].sum(axis=1)) == 1).sum()),
            "All 3 agree (normal)":  int(((anomaly_res[agree_cols].sum(axis=1)) == 0).sum()),
        }
        fig = px.pie(
            names=list(agree_counts.keys()),
            values=list(agree_counts.values()),
            title="Detector Agreement Distribution",
            color_discrete_sequence=px.colors.sequential.Blues_r,
            template="plotly_dark",
        )
        fig.update_layout(paper_bgcolor="#141829")
        st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — SUPPLIER RISK
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("### 🚢 Supplier Risk Intelligence")

    sm = load_json(MODELS_DIR / "supplier_risk_metrics.json")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("High Risk",   f"{sm.get('high_risk_suppliers', 0)}", delta_color="inverse")
    c2.metric("Medium Risk", f"{sm.get('medium_risk_suppliers', 0)}")
    c3.metric("Low Risk",    f"{sm.get('low_risk_suppliers', 0)}")
    c4.metric("Model R²",    f"{sm.get('r2', 0):.4f}")

    sup_results = load_csv(MODELS_DIR / "supplier_risk_results.csv")
    shap_imp    = load_csv(MODELS_DIR / "supplier_shap_importance.csv")

    col_l, col_r = st.columns(2)

    with col_l:
        if not sup_results.empty:
            fig = px.scatter(
                sup_results,
                x="on_time_rate", y="avg_delay_days",
                color="predicted_risk_tier",
                size="avg_defect_units",
                hover_data=["supplier_id"],
                color_discrete_map={"LOW": "#4caf50", "MEDIUM": "#ffb347", "HIGH": "#ff6b6b"},
                title="Supplier Risk Matrix",
                template="plotly_dark",
            )
            fig.update_layout(height=400, paper_bgcolor="#141829", plot_bgcolor="#0a0e1a")
            st.plotly_chart(fig, use_container_width=True)

    with col_r:
        if not shap_imp.empty:
            fig = px.bar(
                shap_imp,
                x="mean_abs_shap", y="feature",
                orientation="h",
                color="mean_abs_shap",
                color_continuous_scale="Oranges",
                title="SHAP Feature Importance — Supplier Risk",
                template="plotly_dark",
            )
            fig.update_layout(height=400, paper_bgcolor="#141829", plot_bgcolor="#0a0e1a",
                              yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig, use_container_width=True)

    # Supplier leaderboard
    if not sup_results.empty:
        st.markdown("### 📋 Supplier Leaderboard")
        display = sup_results[["supplier_id", "on_time_rate", "avg_delay_days",
                                "avg_defect_units", "predicted_risk_score",
                                "predicted_risk_tier"]].copy()
        display.columns = ["Supplier", "On-Time Rate", "Avg Delay (days)",
                           "Avg Defects", "Risk Score", "Risk Tier"]
        display["On-Time Rate"] = display["On-Time Rate"].map("{:.1%}".format)
        display["Avg Delay (days)"] = display["Avg Delay (days)"].round(1)
        display["Risk Score"] = display["Risk Score"].round(4)
        st.dataframe(display.sort_values("Risk Score", ascending=False),
                     use_container_width=True, height=300)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5 — INVENTORY & OPTIMIZATION
# ═══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown("### 📦 Inventory Optimization (EOQ + Safety Stock)")

    im = load_json(MODELS_DIR / "inventory_metrics.json")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Current Annual Cost",  f"${im.get('total_current_cost', 0):,.0f}")
    c2.metric("Optimal Annual Cost",  f"${im.get('total_optimal_cost', 0):,.0f}")
    c3.metric("Total Savings",        f"${im.get('total_savings', 0):,.0f}",
              delta=f"{im.get('savings_pct', 0):.1f}% reduction")
    c4.metric("Avg EOQ",              f"{im.get('avg_eoq', 0):.0f} units")

    inv_opt = load_csv(MODELS_DIR / "inventory_optimization.csv")

    if not inv_opt.empty:
        col_l, col_r = st.columns(2)

        with col_l:
            fig = px.scatter(
                inv_opt,
                x="current_total_cost", y="optimal_total_cost",
                color="cost_savings",
                color_continuous_scale="RdYlGn",
                size="eoq",
                hover_data=["product_id", "category"],
                title="Current vs Optimal Inventory Cost per Product",
                template="plotly_dark",
            )
            max_val = max(inv_opt["current_total_cost"].max(), inv_opt["optimal_total_cost"].max())
            fig.add_shape(type="line", x0=0, y0=0, x1=max_val, y1=max_val,
                          line=dict(color="gray", width=1, dash="dash"))
            fig.update_layout(height=400, paper_bgcolor="#141829", plot_bgcolor="#0a0e1a")
            st.plotly_chart(fig, use_container_width=True)

        with col_r:
            cat_savings = inv_opt.groupby("category")["cost_savings"].sum().reset_index()
            fig = px.bar(
                cat_savings.sort_values("cost_savings", ascending=True),
                x="cost_savings", y="category",
                orientation="h",
                color="cost_savings",
                color_continuous_scale="Greens",
                title="Annual Cost Savings by Category",
                template="plotly_dark",
            )
            fig.update_layout(height=400, paper_bgcolor="#141829", plot_bgcolor="#0a0e1a")
            st.plotly_chart(fig, use_container_width=True)

        # Interactive EOQ explorer
        st.markdown("### 🔬 EOQ Scenario Explorer")
        st.markdown("Adjust parameters to see how EOQ and costs change in real time.")

        ec1, ec2, ec3 = st.columns(3)
        order_cost    = ec1.slider("Ordering Cost ($)", 50, 1000, 200, step=25)
        holding_rate  = ec2.slider("Holding Cost Rate (%/yr)", 10, 50, 25) / 100
        annual_demand = ec3.slider("Annual Demand (units)", 100, 10000, 1000, step=100)

        unit_cost = 50  # example
        eoq_result = np.sqrt(2 * annual_demand * order_cost / (unit_cost * holding_rate))
        orders_per_year = annual_demand / eoq_result
        total_cost = (eoq_result / 2) * (unit_cost * holding_rate) + (annual_demand / eoq_result) * order_cost

        re1, re2, re3 = st.columns(3)
        re1.metric("Optimal Order Qty (EOQ)", f"{eoq_result:.0f} units")
        re2.metric("Orders per Year",         f"{orders_per_year:.1f}")
        re3.metric("Annual Inventory Cost",   f"${total_cost:,.0f}")

        # EOQ sensitivity curve
        demand_range = np.linspace(100, 10000, 100)
        eoq_range = np.sqrt(2 * demand_range * order_cost / (unit_cost * holding_rate))
        cost_range = (eoq_range / 2) * (unit_cost * holding_rate) + (demand_range / eoq_range) * order_cost

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=demand_range, y=eoq_range,
                                 name="EOQ (units)", line=dict(color="#64b5f6")))
        fig.add_trace(go.Scatter(x=demand_range, y=cost_range,
                                 name="Total Cost ($)", line=dict(color="#ff9f40"),
                                 yaxis="y2"))
        fig.update_layout(
            title="EOQ & Total Cost vs Annual Demand",
            template="plotly_dark",
            paper_bgcolor="#141829", plot_bgcolor="#0a0e1a",
            height=350,
            yaxis=dict(title="EOQ (units)", color="#64b5f6"),
            yaxis2=dict(title="Total Cost ($)", color="#ff9f40",
                        overlaying="y", side="right"),
        )
        st.plotly_chart(fig, use_container_width=True)
