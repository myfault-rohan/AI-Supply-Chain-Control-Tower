import streamlit as st
import pandas as pd
import plotly.express as px
from dashboard.utils import fetch_data, no_data_view

st.title("🗺️ Global Risk Map")
st.markdown("### Geographical Supply Chain Intelligence")

# Fetch inventory or warehouse data that might have locations
inventory_df = fetch_data("/inventory")
health_df = fetch_data("/health")

if inventory_df.empty or health_df.empty:
    no_data_view("Geographical Risk Mapping")
else:
    # Merging logic for standard data
    wh_coords = {
        'W1': {'lat': 19.0760, 'lon': 72.8777, 'name': 'Mumbai Terminal'},
        'W2': {'lat': 28.6139, 'lon': 77.2090, 'name': 'Delhi Terminal'},
        'W3': {'lat': 13.0827, 'lon': 80.2707, 'name': 'Chennai Terminal'}
    }
    
    health_full = pd.merge(health_df, inventory_df[['product_id', 'warehouse_id']], on='product_id', how='left')
    
    # Check if there's a 'country' column in ANY uploaded file for secondary mapping
    # This addresses the user's request for "cuntry wise" maps
    has_global_data = False
    
    # Try to find a file with 'country' column in workspace
    import requests
    from dashboard.utils import API_URL
    res = requests.get(f"{API_URL}/workspace_files", params={"username": st.session_state.username})
    if res.status_code == 200:
        files = res.json()
        for f in files:
            if f["type"] == "geospatial":
                st.subheader(f"📍 Global Distribution: `{f['filename']}`")
                geo_data_res = requests.get(f"{API_URL}/data_explorer", params={"username": st.session_state.username, "filename": f["filename"]})
                if geo_data_res.status_code == 200:
                    df_geo = pd.DataFrame(geo_data_res.json())
                    # If it has country, use choropleth or scatter_geo
                    if 'country' in [c.lower() for c in df_geo.columns]:
                        df_geo.columns = [c.lower() for c in df_geo.columns]
                        fig_global = px.choropleth(
                            df_geo, 
                            locations="country", 
                            locationmode='country names',
                            color=df_geo.select_dtypes(include='number').columns[0] if not df_geo.select_dtypes(include='number').empty else None,
                            template="plotly_dark",
                            title="Global Footprint"
                        )
                        st.plotly_chart(fig_global, use_container_width=True)
                        has_global_data = True
                        break

    if not has_global_data:
        st.subheader("📍 Regional Nodes (Supply Chain Infrastructure)")
        health_full['lat'] = health_full['warehouse_id'].map(lambda x: wh_coords.get(x, {}).get('lat', 0))
        health_full['lon'] = health_full['warehouse_id'].map(lambda x: wh_coords.get(x, {}).get('lon', 0))
        health_full['location_name'] = health_full['warehouse_id'].map(lambda x: wh_coords.get(x, {}).get('name', 'Unknown'))

        fig = px.scatter_mapbox(
            health_full,
            lat="lat",
            lon="lon",
            color="health_status",
            size="current_stock",
            hover_name="product_id",
            hover_data=["location_name", "days_until_stockout"],
            color_discrete_map={'GOOD': '#00ff88', 'WARNING': '#ffcc00', 'CRITICAL': '#ff3300'},
            zoom=3,
            height=600,
            template="plotly_dark"
        )
        fig.update_layout(mapbox_style="carto-darkmatter")
        st.plotly_chart(fig, use_container_width=True)
    
    st.info("💡 High-risk nodes are highlighted in red. Bubble size indicates current stock volume.")
