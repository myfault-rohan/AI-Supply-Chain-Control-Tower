import os
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")


def login():
    st.title("AI Supply Chain Control Tower — Dashboard")
    st.subheader("Sign in")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Sign in"):
        try:
            resp = requests.post(f"{API_URL}/token", json={"username": username, "password": password}, timeout=5)
            if resp.status_code == 200:
                token = resp.json().get("access_token")
                st.session_state["token"] = token
                st.success("Signed in")
            else:
                st.error(f"Login failed: {resp.status_code} — {resp.text}")
        except Exception as e:
            st.error(f"Login error: {e}")


def show_dashboard():
    st.title("KPI Dashboard")
    token = st.session_state.get("token")
    if not token:
        st.warning("Please sign in first.")
        return
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = requests.get(f"{API_URL}/dashboard", headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            st.metric("Forecast accuracy", data.get("forecast_accuracy", 0))
            st.metric("Supplier reliability", data.get("supplier_reliability", 0))
            st.metric("Warehouse utilization", data.get("warehouse_utilization", 0))
            st.write("Other KPIs")
            st.json(data)
        else:
            st.error(f"Failed to load dashboard: {resp.status_code}")
    except Exception as e:
        st.error(f"Error fetching dashboard: {e}")


def main():
    if "token" not in st.session_state:
        st.session_state["token"] = None

    if st.session_state.get("token"):
        if st.button("Sign out"):
            st.session_state["token"] = None
            st.experimental_rerun()
    
    if st.session_state.get("token"):
        show_dashboard()
    else:
        login()


if __name__ == "__main__":
    main()
