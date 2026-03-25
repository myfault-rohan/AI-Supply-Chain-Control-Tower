import streamlit as st
import pandas as pd
import requests
import os
import sys

# Add project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")


def get_auth_headers():
    """Get authorization headers with JWT token from session state."""
    token = st.session_state.get("token")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def fetch_data(endpoint, params=None, auth_required=False):
    """Generic helper to fetch data from the API"""
    try:
        headers = get_auth_headers() if auth_required else {}
        response = requests.get(f"{API_URL}{endpoint}", params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data:
                return pd.DataFrame(data)
        elif response.status_code == 401:
            st.error("Authentication required. Please log in again.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return pd.DataFrame()


def api_get(endpoint, params=None, auth_required=True):
    """Make authenticated GET request to API."""
    try:
        headers = get_auth_headers() if auth_required else {}
        response = requests.get(f"{API_URL}{endpoint}", params=params, headers=headers, timeout=10)
        return response
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return None


def api_post(endpoint, params=None, json=None, auth_required=True):
    """Make authenticated POST request to API."""
    try:
        headers = get_auth_headers() if auth_required else {}
        response = requests.post(f"{API_URL}{endpoint}", params=params, json=json, headers=headers, timeout=10)
        return response
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return None


def no_data_view(area_name="this section"):
    """Consistent UI for when no data is available"""
    from dashboard.i18n import t
    st.info(t("no_data", area=area_name))
    st.markdown(t("no_data_hint"))
    if st.button(t("go_to_lab"), key=f"goto_lab_{area_name}"):
        st.switch_page("pages/data_lab.py")


def glass_card(title, value, delta=None, color="normal"):
    """Renders a metric in a premium card-like container"""
    st.metric(label=title, value=value, delta=delta, delta_color=color)
