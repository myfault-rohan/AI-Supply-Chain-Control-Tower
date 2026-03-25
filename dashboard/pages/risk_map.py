import streamlit as st
import pandas as pd
import plotly.express as px
import os, sys, requests

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dashboard.utils import fetch_data, no_data_view, API_URL
from dashboard.i18n import t

st.title(t("risk_map_title"))
st.markdown(f"### {t('risk_map_subtitle')}")

# Fetch inventory or warehouse data that might have locations
inventory_df = fetch_data("/inventory")
health_df = fetch_data("/health")

if inventory_df.empty or health_df.empty:
    no_data_view("Geographical Risk Mapping")
else:
    # Extended warehouse coordinates — global supply chain nodes
    wh_coords = {
        'W1': {'lat': 19.0760, 'lon': 72.8777, 'name': 'Mumbai Terminal', 'country': 'India'},
        'W2': {'lat': 28.6139, 'lon': 77.2090, 'name': 'Delhi Terminal', 'country': 'India'},
        'W3': {'lat': 13.0827, 'lon': 80.2707, 'name': 'Chennai Terminal', 'country': 'India'},
        'W4': {'lat': 35.6762, 'lon': 139.6503, 'name': 'Tokyo Hub', 'country': 'Japan'},
        'W5': {'lat': 34.6937, 'lon': 135.5023, 'name': 'Osaka Hub', 'country': 'Japan'},
        'W6': {'lat': 31.2304, 'lon': 121.4737, 'name': 'Shanghai Port', 'country': 'China'},
        'W7': {'lat': 50.1109, 'lon': 8.6821, 'name': 'Frankfurt Depot', 'country': 'Germany'},
        'W8': {'lat': 41.8781, 'lon': -87.6298, 'name': 'Chicago Center', 'country': 'USA'},
    }
    
    # Merge health data with inventory for warehouse_id
    if "warehouse_id" in inventory_df.columns and "product_id" in health_df.columns:
        health_df["product_id"] = health_df["product_id"].astype(str)
        inventory_df["product_id"] = inventory_df["product_id"].astype(str)
        health_full = pd.merge(health_df, inventory_df[['product_id', 'warehouse_id']], on='product_id', how='left')
    else:
        health_full = health_df.copy()
        if "warehouse_id" not in health_full.columns:
            health_full["warehouse_id"] = "W1"
    
    # Check for uploaded geospatial data
    has_global_data = False
    try:
        res = requests.get(f"{API_URL}/workspace_files", params={"username": st.session_state.username}, timeout=5)
        if res.status_code == 200:
            files = res.json()
            for f in files:
                if f.get("type") == "geospatial":
                    st.subheader(f"📍 Global Distribution: `{f['filename']}`")
                    geo_data_res = requests.get(
                        f"{API_URL}/data_explorer", 
                        params={"username": st.session_state.username, "filename": f["filename"]},
                        timeout=10
                    )
                    if geo_data_res.status_code == 200:
                        df_geo = pd.DataFrame(geo_data_res.json())
                        lower_cols = [c.lower() for c in df_geo.columns]
                        if 'country' in lower_cols:
                            df_geo.columns = [c.lower() for c in df_geo.columns]
                            numeric_cols = df_geo.select_dtypes(include='number').columns
                            color_col = numeric_cols[0] if len(numeric_cols) > 0 else None
                            fig_global = px.choropleth(
                                df_geo, 
                                locations="country", 
                                locationmode='country names',
                                color=color_col,
                                template="plotly_dark",
                                title="🌍 Global Supply Chain Footprint",
                                color_continuous_scale="Viridis"
                            )
                            fig_global.update_layout(height=500)
                            st.plotly_chart(fig_global, use_container_width=True)
                            has_global_data = True
                            break
    except:
        pass

    if not has_global_data:
        st.subheader(t("regional_nodes"))
        
        # Filter controls
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            if "health_status" in health_full.columns:
                status_filter = st.multiselect(
                    "Filter by Status", 
                    options=["GOOD", "WARNING", "CRITICAL"],
                    default=["GOOD", "WARNING", "CRITICAL"]
                )
                health_full = health_full[health_full["health_status"].isin(status_filter)]
        
        health_full['lat'] = health_full['warehouse_id'].map(lambda x: wh_coords.get(x, {}).get('lat', 20.0))
        health_full['lon'] = health_full['warehouse_id'].map(lambda x: wh_coords.get(x, {}).get('lon', 78.0))
        health_full['location_name'] = health_full['warehouse_id'].map(lambda x: wh_coords.get(x, {}).get('name', 'Unknown'))

        fig = px.scatter_mapbox(
            health_full,
            lat="lat",
            lon="lon",
            color="health_status" if "health_status" in health_full.columns else None,
            size="current_stock" if "current_stock" in health_full.columns else None,
            hover_name="product_id" if "product_id" in health_full.columns else None,
            hover_data=["location_name", "days_until_stockout"] if "days_until_stockout" in health_full.columns else ["location_name"],
            color_discrete_map={'GOOD': '#00ff88', 'WARNING': '#ffcc00', 'CRITICAL': '#ff3300'},
            zoom=2,
            height=600,
            template="plotly_dark"
        )
        fig.update_layout(mapbox_style="carto-darkmatter")
        st.plotly_chart(fig, use_container_width=True)
    
    st.info(t("risk_map_tip"))
