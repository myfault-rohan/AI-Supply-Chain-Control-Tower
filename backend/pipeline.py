import os
import subprocess
import sys
import pandas as pd
import shutil

# Configuration
DATASET_DIR = 'dataset'
PROCESSED_DATA_DIR = os.path.join(DATASET_DIR, 'processed files')

def run_script(script_path):
    """Run a python script and return success status"""
    print(f"Running {script_path}...")
    try:
        result = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"Successfully ran {script_path}")
            return True
        else:
            print(f"Error running {script_path}: {result.stderr}")
            return False
    except Exception as e:
        print(f"Exception running {script_path}: {e}")
        return False

def sync_workspace_to_dataset(username):
    """Copy files from user workspace to root dataset for processing if they exist"""
    workspace_dir = os.path.join(DATASET_DIR, 'workspaces', username)
    if not os.path.exists(workspace_dir):
        return
    
    # Mapping of expected filenames to root dataset paths
    file_mapping = {
        'inventory.csv': os.path.join(DATASET_DIR, 'stream_inventory.csv'),
        'sales.csv': os.path.join(DATASET_DIR, 'stream_sales.csv'),
        'suppliers.csv': os.path.join(DATASET_DIR, 'stream_suppliers.csv'),
        'shipments.csv': os.path.join(DATASET_DIR, 'stream_shipments.csv'),
        'warehouses.csv': os.path.join(DATASET_DIR, 'warehouses.csv'),
    }
    
    for filename, target_path in file_mapping.items():
        source_path = os.path.join(workspace_dir, filename)
        if os.path.exists(source_path):
            print(f"Syncing {filename} from {username}'s workspace to {target_path}")
            shutil.copy2(source_path, target_path)

def run_pipeline(username):
    """Run the full data processing pipeline"""
    print(f"--- Starting Pipeline for user: {username} ---")
    
    # 1. Sync workspace files to main dataset
    sync_workspace_to_dataset(username)
    
    # 2. Run Spark Processing (or simplified version)
    # Note: spark_processing.py expects stream_inventory.csv, stream_sales.csv, stream_shipments.csv
    if not run_script('spark_processing/spark_processing.py'):
        print("Pipeline failed at Spark processing step.")
        # We continue anyway to try other steps if possible, or return failure
    
    # 3. Run Demand Forecaster
    if not run_script('ml_models/demand_forecaster.py'):
        print("Pipeline failed at demand forecasting step.")
    
    # 4. Run Reorder Optimizer
    if not run_script('risk_engine/reorder_optimizer.py'):
        print("Pipeline failed at reorder optimization step.")
        
    # 5. Run Health Score Engine
    if not run_script('risk_engine/health_score_engine.py'):
        print("Pipeline failed at health scoring step.")
    
    # 6. Run Analytics
    run_script('feature_engineering/cost_analytics.py')
    run_script('feature_engineering/supplier_analytics.py')
    run_script('feature_engineering/warehouse_analytics.py')

    print("--- Pipeline Execution Finished ---")

if __name__ == "__main__":
    import sys
    user = sys.argv[1] if len(sys.argv) > 1 else "default"
    run_pipeline(user)
