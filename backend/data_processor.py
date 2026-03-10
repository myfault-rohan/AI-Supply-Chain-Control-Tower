import os
import pandas as pd
import subprocess
import sys
import shutil

# Configuration
DATASET_DIR = "dataset"
UPLOAD_DIR = os.path.join(DATASET_DIR, "uploads")
PROCESSED_DATA_DIR = os.path.join(DATASET_DIR, "processed files")

# Mapping of required columns to their respective target filenames
DATA_TYPE_MAP = {
    "inventory": {
        "columns": ["product_id", "current_stock", "safety_stock"],
        "target": "inventory.csv"
    },
    "sales": {
        "columns": ["product_id", "daily_sales", "date"],
        "target": "sales.csv"
    },
    "suppliers": {
        "columns": ["supplier_id", "supplier_name", "lead_time_days"],
        "target": "suppliers.csv"
    },
    "shipments": {
        "columns": ["shipment_id", "supplier_id", "product_id", "actual_delivery"],
        "target": "shipments.csv"
    },
    "warehouses": {
        "columns": ["warehouse_id", "warehouse_location", "capacity"],
        "target": "warehouses.csv"
    }
}

def detect_data_type(file_path):
    """Detects the type of supply chain data based on CSV headers or generic themes."""
    try:
        df = pd.read_csv(file_path, nrows=5)
        headers = [c.lower() for c in df.columns]
        
        # 1. Check for standard supply chain types
        for data_type, info in DATA_TYPE_MAP.items():
            if all(col in headers for col in info["columns"]):
                return data_type
        
        # 2. Check for Geographical Data
        geo_cols = ["country", "state", "city", "latitude", "longitude", "lat", "lon"]
        if any(col in headers for col in geo_cols):
            return "geospatial"
            
        # 3. Check for Time Series / Financial Data
        time_cols = ["date", "timestamp", "time", "year", "month"]
        val_cols = ["amount", "value", "price", "revenue", "cost"]
        if any(col in headers for col in time_cols) and any(col in headers for col in val_cols):
            return "timeseries"
            
        return "generic"
    except Exception as e:
        print(f"Error detecting data type for {file_path}: {e}")
    return "unknown"

def run_script(script_path):
    """Run a python script and return success status"""
    print(f"Executing: {script_path}")
    try:
        full_script_path = os.path.join(os.getcwd(), script_path)
        if not os.path.exists(full_script_path):
            print(f"Warning: Script {script_path} not found")
            return False
            
        result = subprocess.run([sys.executable, full_script_path], capture_output=True, text=True)
        return result.returncode == 0
    except Exception as e:
        print(f"Exception running {script_path}: {e}")
        return False

def process_uploaded_data(username="default"):
    """
    1. Identifies uploaded files
    2. Synchronizes standard supply chain data
    3. Handles generic/extra data for the Data Explorer
    4. Triggers the analytics pipeline
    """
    print(f"\n--- Starting Enterprise Data Processing for: {username} ---")
    
    workspace_dir = os.path.join(DATASET_DIR, "workspaces", username)
    if not os.path.exists(workspace_dir):
        print(f"No workspace found for {username}")
        return
    
    # 1. Detect and Sync
    uploaded_files = [f for f in os.listdir(workspace_dir) if f.endswith(('.csv', '.xlsx', '.json'))]
    has_standard_data = False
    
    # Meta-information for generic explorer
    generic_metadata = []
    
    for filename in uploaded_files:
        file_path = os.path.join(workspace_dir, filename)
        data_type = detect_data_type(file_path)
        
        metadata = {
            "filename": filename,
            "type": data_type,
            "rows": 0,
            "cols": 0
        }
        
        # Load briefly for metadata
        try:
            df_temp = pd.read_csv(file_path, nrows=10)
            metadata["rows"] = len(pd.read_csv(file_path)) # Actually counting rows might be slow for huge files, but for now it's okay
            metadata["cols"] = len(df_temp.columns)
        except: pass

        if data_type in DATA_TYPE_MAP:
            target_name = DATA_TYPE_MAP[data_type]["target"]
            target_path = os.path.join(DATASET_DIR, target_name)
            shutil.copy2(file_path, target_path)
            
            # Sync to 'stream_' versions for Spark/Legacy components
            if data_type in ["inventory", "sales", "suppliers", "shipments"]:
                stream_target = os.path.join(DATASET_DIR, f"stream_{target_name}")
                shutil.copy2(file_path, stream_target)
            has_standard_data = True
            
        generic_metadata.append(metadata)

    # Save metadata for the Data Management Lab
    meta_df = pd.DataFrame(generic_metadata)
    os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
    meta_df.to_csv(os.path.join(PROCESSED_DATA_DIR, "workspace_metadata.csv"), index=False)

    # 2. Run Analytics Pipeline IF standard data is present
    if has_standard_data:
        scripts = [
            "ml_models/demand_forecaster.py",
            "risk_engine/reorder_optimizer.py",
            "risk_engine/health_score_engine.py",
            "feature_engineering/cost_analytics.py",
            "feature_engineering/supplier_analytics.py",
            "feature_engineering/warehouse_analytics.py",
            "risk_engine/global_risk_dashboard.py",
            "reporting/daily_report_generator.py"
        ]
        for script in scripts:
            run_script(script)
    else:
        print("No standard supply chain data detected. Skipping analytics pipeline.")

    print("--- Enterprise Data Processing Complete ---\n")

if __name__ == "__main__":
    process_uploaded_data()
