import streamlit as st
import pandas as pd
import requests
import os

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

def fetch_data(endpoint, params=None):
    """Generic helper to fetch data from the API"""
    try:
        response = requests.get(f"{API_URL}{endpoint}", params=params)
        if response.status_code == 200:
            return pd.DataFrame(response.json())
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return pd.DataFrame()

def no_data_view(area_name="this section"):
    """Consistent UI for when no data is available"""
    st.info(f"🌑 **No data available for {area_name}.**")
    st.markdown(f"""
    It looks like no relevant files have been uploaded yet. 
    Please head over to the **Data Management Lab** to upload your supply chain CSVs.
    """)
    if st.button("Go to Data Lab", key=f"goto_lab_{area_name}"):
        st.switch_page("pages/data_lab.py")

def glass_card(title, value, delta=None, color="normal"):
    """Renders a metric in a premium card-like container"""
    st.metric(label=title, value=value, delta=delta, delta_color=color)
