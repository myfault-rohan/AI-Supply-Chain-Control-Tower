import streamlit as st
import pandas as pd
import requests
import os
from dashboard.utils import API_URL, no_data_view

st.title("🔍 Data Management Lab")
st.markdown("### Enterprise Data Ingestion & Exploration")

# --- 1. Multi-File Upload Section ---
st.subheader("📤 Bulk Data Ingestion")
uploaded_files = st.file_uploader(
    "Drop your CSV, Excel, or JSON files here", 
    type=["csv", "xlsx", "json"],
    accept_multiple_files=True
)

if uploaded_files:
    if st.button("🚀 Process Data Stream"):
        with st.spinner("Analyzing and indexing files..."):
            files_payload = [("files", (uf.name, uf.getvalue(), "text/csv")) for uf in uploaded_files]
            response = requests.post(
                f"{API_URL}/upload_data",
                params={"username": st.session_state.username},
                files=files_payload
            )
            if response.status_code == 200:
                st.success("✅ Files processed and analytics updated.")
                st.balloons()
                st.rerun()
            else:
                st.error("❌ Upload failed.")

st.markdown("---")

# --- 2. Workspace Explorer ---
st.subheader("📂 Workspace Explorer")
response = requests.get(f"{API_URL}/workspace_files", params={"username": st.session_state.username})

if response.status_code == 200:
    files = response.json()
    if not files:
        no_data_view("Workspace Storage")
    else:
        # Display as a clean table
        df_files = pd.DataFrame(files)
        st.dataframe(df_files, use_container_width=True)
        
        # --- 3. Generic Data Previewer ---
        selected_file = st.selectbox("Select a file to explore", options=[f["filename"] for f in files])
        
        if selected_file:
            st.markdown(f"#### Preview: `{selected_file}`")
            preview_res = requests.get(
                f"{API_URL}/data_explorer", 
                params={"username": st.session_state.username, "filename": selected_file}
            )
            if preview_res.status_code == 200:
                df_preview = pd.DataFrame(preview_res.json())
                st.dataframe(df_preview, use_container_width=True)
                
                # Dynamic Charts for Generic Data
                st.markdown("#### 📊 Instant Analytics")
                numeric_cols = df_preview.select_dtypes(include=['number']).columns.tolist()
                if len(numeric_cols) >= 1:
                    chart_col = st.selectbox("Select column to visualize", numeric_cols)
                    st.bar_chart(df_preview[chart_col])
                else:
                    st.info("No numeric columns detected for instant visualization.")
else:
    st.error("Could not fetch workspace files.")
