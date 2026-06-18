"""
dashboard/app.py
================
Seller Risk Triage Dashboard for Olist Account Managers.
Connects to the FastAPI backend to retrieve XGBoost predictions and SHAP explanations.
"""

import streamlit as st
import pandas as pd
import requests
import plotly.express as px

# ── Configuration ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Olist Seller Risk Triage",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

API_BASE_URL = "http://127.0.0.1:8000/api/v1"

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
  .stApp { background: #0a0e17; }
  
  [data-testid="metric-container"] {
    background: #141b2d;
    border: 1px solid #1f2937;
    border-radius: 8px;
    padding: 16px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.3);
  }
  
  .risk-card {
    background: #141b2d;
    border: 1px solid #1f2937;
    border-left: 4px solid #3b82f6;
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 16px;
  }
  .risk-card.critical { border-left-color: #ef4444; }
  .risk-card.warning { border-left-color: #f59e0b; }
  .risk-card.good { border-left-color: #10b981; }
  
  .driver-tag {
    display: inline-block;
    background: #1f2937;
    color: #9ca3af;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 0.8rem;
    margin-right: 8px;
    margin-top: 4px;
  }
</style>
""", unsafe_allow_html=True)

# ── Data Loading ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def fetch_risk_data(tier=None):
    try:
        url = f"{API_BASE_URL}/seller-risk?limit=500"
        if tier and tier != "ALL":
            url += f"&tier={tier}"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to connect to API: {e}")
        return []

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🚨 Risk Triage")
    st.markdown("Filter sellers by predicted churn risk.")
    
    tier_filter = st.radio(
        "Risk Tier",
        ["ALL", "CRITICAL", "WARNING", "GOOD"],
        index=1
    )
    
    st.markdown("---")
    st.markdown("**Model Info**")
    st.markdown("- **Algorithm**: XGBoost")
    st.markdown("- **Window**: 8 Weeks")
    st.markdown("- **Horizon**: 45 Days")
    st.markdown("- **Recall**: 73.5%")

# ── Main UI ──────────────────────────────────────────────────────────────────
st.title("Olist Seller Risk Triage System")
st.markdown("Identify and intervene with high-value sellers before they leave the platform.")

# Fetch data
data = fetch_risk_data(tier_filter)

if not data:
    st.warning("No data returned from API. Is the FastAPI server running?")
    st.stop()

df = pd.DataFrame(data)

# Metrics
c1, c2, c3 = st.columns(3)
c1.metric("Sellers in View", f"{len(df):,}")
c2.metric("Critical Risk Sellers", f"{len(df[df['risk_tier'] == 'CRITICAL']):,}")
c3.metric("Revenue at Risk (30d)", f"${df['revenue_at_risk'].sum():,.2f}")

st.markdown("---")

# Visualizations
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    fig = px.scatter(
        df,
        x="churn_probability",
        y="revenue_at_risk",
        color="risk_tier",
        hover_data=["seller_id"],
        color_discrete_map={"CRITICAL": "#ef4444", "WARNING": "#f59e0b", "GOOD": "#10b981"},
        title="Revenue at Risk vs Churn Probability",
        template="plotly_dark",
        labels={"churn_probability": "Churn Probability", "revenue_at_risk": "30-Day Revenue at Risk ($)"}
    )
    fig.update_layout(paper_bgcolor="#0a0e17", plot_bgcolor="#141b2d")
    st.plotly_chart(fig, use_container_width=True)

with col_chart2:
    # Top drivers across these sellers
    all_drivers = []
    for s in data:
        for d in s.get("top_drivers", []):
            all_drivers.append({"feature": d["feature"], "impact": d["shap_impact"]})
            
    if all_drivers:
        driver_df = pd.DataFrame(all_drivers).groupby("feature")["impact"].mean().reset_index()
        driver_df = driver_df.sort_values("impact", ascending=True).tail(5)
        
        fig2 = px.bar(
            driver_df,
            x="impact",
            y="feature",
            orientation="h",
            title="Avg SHAP Impact for Displayed Sellers",
            template="plotly_dark"
        )
        fig2.update_layout(paper_bgcolor="#0a0e17", plot_bgcolor="#141b2d")
        st.plotly_chart(fig2, use_container_width=True)

st.markdown("### Action Queue")

# Render Seller Cards
for s in data[:20]: # Show top 20
    tier_class = s["risk_tier"].lower()
    
    # Format drivers
    drivers_html = ""
    for d in s.get("top_drivers", []):
        feat = d["feature"].replace("_", " ").title()
        drivers_html += f'<span class="driver-tag">{feat} (+{(d["shap_impact"]*100):.1f}%)</span>'
        
    st.markdown(f"""
    <div class="risk-card {tier_class}">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div>
                <h4 style="margin: 0; color: #e5e7eb;">Seller: <code>{s['seller_id'][:8]}...</code></h4>
                <div style="font-size: 0.9rem; color: #9ca3af; margin-top: 4px;">
                    State: {s['seller_state']} | Rev at Risk: <b>${s['revenue_at_risk']:,.2f}</b> | 30d Orders: {s['metrics']['orders_30d']}
                </div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 1.5rem; font-weight: 700; color: {'#ef4444' if tier_class == 'critical' else '#f59e0b' if tier_class == 'warning' else '#10b981'};">
                    {s['churn_probability']*100:.1f}%
                </div>
                <div style="font-size: 0.8rem; color: #9ca3af; text-transform: uppercase; letter-spacing: 1px;">
                    {s['risk_tier']}
                </div>
            </div>
        </div>
        <div style="margin-top: 12px; font-size: 0.85rem; color: #d1d5db;">
            <b>Why flagged?</b><br>
            {drivers_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

if len(data) > 20:
    st.info(f"Showing top 20 out of {len(data)} sellers in this view.")
