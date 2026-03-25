"""
Enterprise Data Processor
Detects uploaded data types, creates the processed supply chain dataset using pure pandas
(no Spark dependency), and triggers the full analytics pipeline.
"""

import os
import pandas as pd
import numpy as np
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
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path, nrows=5)
        elif file_path.endswith('.xlsx'):
            df = pd.read_excel(file_path, nrows=5)
        elif file_path.endswith('.json'):
            df = pd.read_json(file_path).head(5)
        else:
            return "unknown"

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

def create_processed_supply_chain():
    """
    Creates the processed_supply_chain.csv using pure pandas.
    This replaces the Spark processing step so the pipeline works without PySpark.
    Merges inventory, sales, and shipments data with calculated analytics fields.
    """
    print("\n--- Creating Processed Supply Chain Dataset (Pandas) ---")
    
    inventory_file = os.path.join(DATASET_DIR, "inventory.csv")
    sales_file = os.path.join(DATASET_DIR, "sales.csv")
    shipments_file = os.path.join(DATASET_DIR, "shipments.csv")
    output_file = os.path.join(DATASET_DIR, "processed_supply_chain.csv")
    
    # Check minimum required files
    if not os.path.exists(inventory_file):
        print(f"Warning: {inventory_file} not found. Cannot create processed dataset.")
        return False
    
    try:
        # 1. Load inventory
        inventory_df = pd.read_csv(inventory_file)
        inventory_df = inventory_df.fillna({"current_stock": 0, "safety_stock": 0, "reorder_point": 0})
        print(f"  Loaded {len(inventory_df)} inventory records")
        
        # 2. Load and aggregate sales
        if os.path.exists(sales_file):
            sales_df = pd.read_csv(sales_file)
            sales_df["daily_sales"] = pd.to_numeric(sales_df["daily_sales"], errors="coerce").fillna(0)
            
            # Calculate average daily sales per product
            sales_agg = sales_df.groupby("product_id").agg(
                avg_daily_sales=("daily_sales", "mean"),
                total_daily_sales=("daily_sales", "sum"),
                stddev_daily_sales=("daily_sales", "std")
            ).reset_index()
            sales_agg["stddev_daily_sales"] = sales_agg["stddev_daily_sales"].fillna(0)
            
            # Detect demand spikes (daily_sales > 1.5 * rolling average)
            sales_df_sorted = sales_df.sort_values(["product_id", "date"])
            sales_df_sorted["rolling_avg"] = sales_df_sorted.groupby("product_id")["daily_sales"].transform(
                lambda x: x.rolling(window=7, min_periods=1).mean()
            )
            sales_df_sorted["is_spike"] = sales_df_sorted["daily_sales"] > 1.5 * sales_df_sorted["rolling_avg"]
            spike_counts = sales_df_sorted.groupby("product_id")["is_spike"].sum().reset_index()
            spike_counts.columns = ["product_id", "total_spikes"]
            
            # Check if any product currently has a demand spike (latest record)
            latest_sales = sales_df_sorted.groupby("product_id").last().reset_index()
            latest_sales = latest_sales[["product_id", "is_spike"]].rename(columns={"is_spike": "demand_spike"})
            
            sales_agg = sales_agg.merge(spike_counts, on="product_id", how="left")
            sales_agg = sales_agg.merge(latest_sales, on="product_id", how="left")
            sales_agg["total_spikes"] = sales_agg["total_spikes"].fillna(0).astype(int)
            sales_agg["demand_spike"] = sales_agg["demand_spike"].fillna(False)
            
            print(f"  Processed {len(sales_df)} sales records")
        else:
            # Create default sales aggregation from inventory daily_demand if available
            if "daily_demand" in inventory_df.columns:
                sales_agg = inventory_df[["product_id", "daily_demand"]].copy()
                sales_agg = sales_agg.rename(columns={"daily_demand": "avg_daily_sales"})
                sales_agg["total_daily_sales"] = sales_agg["avg_daily_sales"]
                sales_agg["stddev_daily_sales"] = 0
                sales_agg["total_spikes"] = 0
                sales_agg["demand_spike"] = False
            else:
                sales_agg = pd.DataFrame({
                    "product_id": inventory_df["product_id"],
                    "avg_daily_sales": 1.0,
                    "total_daily_sales": 1.0,
                    "stddev_daily_sales": 0.0,
                    "total_spikes": 0,
                    "demand_spike": False
                })
            print("  No sales.csv found, using defaults")
        
        # 3. Load and aggregate shipments
        if os.path.exists(shipments_file):
            shipments_df = pd.read_csv(shipments_file)
            
            # Calculate delay days
            shipments_df["expected_delivery"] = pd.to_datetime(shipments_df["expected_delivery"], errors="coerce")
            shipments_df["actual_delivery"] = pd.to_datetime(shipments_df["actual_delivery"], errors="coerce")
            shipments_df["delay_days"] = (shipments_df["actual_delivery"] - shipments_df["expected_delivery"]).dt.days
            shipments_df["delay_days"] = shipments_df["delay_days"].fillna(0)
            shipments_df["is_delayed"] = shipments_df["delay_days"] > 0
            
            shipments_agg = shipments_df.groupby("product_id").agg(
                total_delays=("is_delayed", "sum"),
                avg_delay_days=("delay_days", "mean")
            ).reset_index()
            
            print(f"  Processed {len(shipments_df)} shipment records")
        else:
            shipments_agg = pd.DataFrame(columns=["product_id", "total_delays", "avg_delay_days"])
            print("  No shipments.csv found, using defaults")
        
        # 4. Merge everything on product_id
        merged = inventory_df.merge(sales_agg, on="product_id", how="left")
        merged = merged.merge(shipments_agg, on="product_id", how="left")
        
        # Fill NaN values
        merged["avg_daily_sales"] = merged["avg_daily_sales"].fillna(1.0)
        merged["total_daily_sales"] = merged["total_daily_sales"].fillna(0)
        merged["stddev_daily_sales"] = merged["stddev_daily_sales"].fillna(0)
        merged["total_spikes"] = merged["total_spikes"].fillna(0).astype(int)
        merged["demand_spike"] = merged["demand_spike"].fillna(False)
        merged["total_delays"] = merged["total_delays"].fillna(0).astype(int)
        merged["avg_delay_days"] = merged["avg_delay_days"].fillna(0)
        
        # 5. Calculate inventory_days
        merged["inventory_days"] = np.where(
            merged["avg_daily_sales"] > 0,
            merged["current_stock"] / merged["avg_daily_sales"],
            9999
        )
        
        # 6. Save output
        os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True)
        merged.to_csv(output_file, index=False)
        
        print(f"  ✅ Processed supply chain dataset saved: {output_file}")
        print(f"  Total records: {len(merged)}")
        return True
        
    except Exception as e:
        print(f"  ❌ Error creating processed supply chain: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_script(script_path):
    """Run a python script and return success status"""
    print(f"Executing: {script_path}")
    try:
        full_script_path = os.path.join(os.getcwd(), script_path)
        if not os.path.exists(full_script_path):
            print(f"Warning: Script {script_path} not found")
            return False
            
        result = subprocess.run(
            [sys.executable, full_script_path], 
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            print(f"  ✅ {script_path} completed successfully")
        else:
            print(f"  ❌ {script_path} failed: {result.stderr[:500]}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"  ⏱ {script_path} timed out after 120s")
        return False
    except Exception as e:
        print(f"  ❌ Exception running {script_path}: {e}")
        return False

def process_uploaded_data(username="default"):
    """
    Enterprise Data Processing Pipeline:
    1. Identifies uploaded files and detects their data types
    2. Synchronizes standard supply chain data to root dataset dir
    3. Creates merged processed_supply_chain.csv (pandas-based, no Spark)
    4. Triggers the full analytics pipeline
    """
    print(f"\n{'='*60}")
    print(f"  Enterprise Data Processing — User: {username}")
    print(f"{'='*60}")
    
    workspace_dir = os.path.join(DATASET_DIR, "workspaces", username)
    if not os.path.exists(workspace_dir):
        print(f"No workspace found for {username}")
        return
    
    # 1. Detect and Sync uploaded files
    uploaded_files = [f for f in os.listdir(workspace_dir) if f.endswith(('.csv', '.xlsx', '.json'))]
    has_standard_data = False
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
        
        try:
            if filename.endswith('.csv'):
                df_temp = pd.read_csv(file_path)
            elif filename.endswith('.xlsx'):
                df_temp = pd.read_excel(file_path)
            elif filename.endswith('.json'):
                df_temp = pd.read_json(file_path)
            else:
                df_temp = pd.DataFrame()
            metadata["rows"] = len(df_temp)
            metadata["cols"] = len(df_temp.columns)
        except:
            pass

        if data_type in DATA_TYPE_MAP:
            target_name = DATA_TYPE_MAP[data_type]["target"]
            target_path = os.path.join(DATASET_DIR, target_name)
            shutil.copy2(file_path, target_path)
            print(f"  📁 Synced {filename} → {target_path} (type: {data_type})")
            
            # Also copy to stream_ versions for Spark/Legacy components
            if data_type in ["inventory", "sales", "suppliers", "shipments"]:
                stream_target = os.path.join(DATASET_DIR, f"stream_{target_name}")
                shutil.copy2(file_path, stream_target)
            has_standard_data = True
            
        generic_metadata.append(metadata)

    # Save metadata for the Data Management Lab
    meta_df = pd.DataFrame(generic_metadata)
    os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
    meta_df.to_csv(os.path.join(PROCESSED_DATA_DIR, "workspace_metadata.csv"), index=False)

    # 2. Create processed supply chain dataset (replaces Spark step)
    if has_standard_data:
        print("\n--- Step 1/3: Creating Processed Supply Chain Dataset ---")
        if not create_processed_supply_chain():
            print("⚠ Could not create processed dataset, but continuing with pipeline...")
        
        # 3. Run Analytics Pipeline
        print("\n--- Step 2/3: Running Analytics Pipeline ---")
        scripts = [
            "ml_models/demand_forecaster.py",
            "risk_engine/reorder_optimizer.py",
            "risk_engine/health_score_engine.py",
            "feature_engineering/cost_analytics.py",
            "feature_engineering/supplier_analytics.py",
            "feature_engineering/warehouse_analytics.py",
        ]
        for script in scripts:
            run_script(script)
        
        # Run global risk dashboard and report generator last (depends on above outputs)
        print("\n--- Step 3/3: Generating Reports ---")
        run_script("risk_engine/global_risk_dashboard.py")
        run_script("reporting/daily_report_generator.py")
    else:
        print("\n⚠ No standard supply chain data detected. Skipping analytics pipeline.")
        print("  Upload inventory, sales, suppliers, shipments, or warehouses CSVs to trigger analysis.")

    print(f"\n{'='*60}")
    print(f"  Enterprise Data Processing Complete")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    process_uploaded_data()
