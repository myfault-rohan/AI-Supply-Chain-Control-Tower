import os
import shutil
import pandas as pd
from typing import List, Dict, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File

app = FastAPI(
    title="AI Supply Chain Control Tower API",
    description="Backend API for querying supply chain inventory, forecasts, and reorder recommendations.",
    version="1.0.0"
)

# File Paths
PROCESSED_DATA_DIR = 'dataset/processed files'
DEMAND_FILE = os.path.join(PROCESSED_DATA_DIR, 'demand_predictions.csv')
REORDER_FILE = os.path.join(PROCESSED_DATA_DIR, 'reorder_recommendations.csv')
HEALTH_FILE = os.path.join(PROCESSED_DATA_DIR, 'supply_chain_health.csv')
LIVE_INVENTORY_DIR = 'dataset/live_supply_chain'
UPLOAD_DIR = 'dataset/uploads'

# Ensure upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

def load_dataset(filepath: str) -> pd.DataFrame:
    """Helper to load a CSV dataset"""
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"Dataset {filepath} not found. Please run the data pipelines first.")
    return pd.read_csv(filepath)

@app.get("/")
def read_root():
    return {"message": "Welcome to the AI Supply Chain Control Tower API. Visit /docs for documentation."}

@app.get("/inventory", response_model=List[Dict])
def get_inventory():
    """Returns the current inventory status for all products."""
    df = load_dataset(DEMAND_FILE)
    # Selecting relevant inventory columns
    inventory_cols = ['product_id', 'warehouse_id', 'current_stock', 'safety_stock', 'reorder_point', 'inventory_days']
    return df[inventory_cols].to_dict(orient='records')

@app.get("/demand_forecast", response_model=List[Dict])
def get_demand_forecast():
    """Returns predicted demand for all products."""
    df = load_dataset(DEMAND_FILE)
    forecast_cols = ['product_id', 'predicted_demand', 'avg_daily_sales', 'demand_spike']
    return df[forecast_cols].to_dict(orient='records')

@app.get("/reorder_recommendations", response_model=List[Dict])
def get_reorder_recommendations():
    """Returns reorder recommendations including quantities and lead times."""
    df = load_dataset(REORDER_FILE)
    return df[['product_id', 'reorder_quantity', 'supplier_lead_time', 'alert_message']].to_dict(orient='records')

@app.get("/alerts", response_model=List[Dict])
def get_alerts():
    """Returns urgent supply chain alerts for products at high risk of stockout."""
    df = load_dataset(REORDER_FILE)
    alerts_df = df[df['stockout_risk'] == True]
    return alerts_df[['product_id', 'days_until_stockout', 'alert_message']].to_dict(orient='records')

@app.get("/health", response_model=List[Dict])
def get_health():
    """Returns the supply chain health metrics and statuses."""
    df = load_dataset(HEALTH_FILE)
    return df.to_dict(orient='records')

@app.get("/live_inventory", response_model=List[Dict])
def get_live_inventory():
    """Returns the latest entries from the live streaming supply chain data directory."""
    live_dir = 'dataset/live_supply_chain'
    if not os.path.exists(live_dir) or not os.path.isdir(live_dir):
        raise HTTPException(
            status_code=404, 
            detail="Live streaming data directory not found. Ensure the Spark streaming processor is running."
        )
    
    try:
        # Get all CSV files in the directory
        files = [os.path.join(live_dir, f) for f in os.listdir(live_dir) if f.endswith('.csv')]
        if not files:
            return []
        
        # Load and combine latest data (simplified: just read the most recent one for now or all)
        # For simplicity in this dashboard context, we read existing ones
        dfs = [pd.read_csv(f) for f in files]
        if not dfs:
            return []
        
        combined_df = pd.concat(dfs, ignore_index=True)
        return combined_df.tail(100).to_dict(orient='records')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading live data: {str(e)}")

@app.get("/live_alerts")
def get_live_alerts():
    """Returns the latest alerts from the supply chain monitoring system."""
    import pandas as pd
    import os

    file_path = "dataset/live_alerts.csv"

    if not os.path.exists(file_path):
        return []

    try:
        df = pd.read_csv(file_path)
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading alerts data: {str(e)}")

@app.get("/supplier_performance")
def get_supplier_performance():
    """Endpoint to fetch supplier performance metrics."""
    file_path = os.path.join(PROCESSED_DATA_DIR, "supplier_performance.csv")

    if not os.path.exists(file_path):
        return []

    try:
        df = pd.read_csv(file_path)
        return df.fillna(0).to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading supplier performance data: {str(e)}")

@app.get("/warehouse_utilization")
def get_warehouse_utilization():
    """Endpoint to fetch warehouse utilization metrics."""
    file_path = os.path.join(PROCESSED_DATA_DIR, "warehouse_utilization.csv")

    if not os.path.exists(file_path):
        return []

    try:
        df = pd.read_csv(file_path)
        return df.fillna(0).to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading warehouse utilization data: {str(e)}")

@app.get("/cost_analysis")
def get_cost_analysis():
    """Endpoint to fetch supply chain cost analysis."""
    file_path = os.path.join(PROCESSED_DATA_DIR, "cost_analysis.csv")

    if not os.path.exists(file_path):
        return []

    try:
        df = pd.read_csv(file_path)
        return df.fillna(0).to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading cost analysis data: {str(e)}")

@app.get("/global_risk_summary")
def get_global_risk_summary():
    """Endpoint to fetch aggregated global risk summary."""
    file_path = os.path.join(PROCESSED_DATA_DIR, "global_risk_summary.csv")

    if not os.path.exists(file_path):
        return []

    try:
        df = pd.read_csv(file_path)
        return df.fillna(0).to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading global risk summary: {str(e)}")

@app.get("/daily_report")
def get_daily_report():
    """Endpoint to fetch the latest daily supply chain report."""
    file_path = "reports/daily_supply_chain_report.csv"

    if not os.path.exists(file_path):
        return []

    try:
        df = pd.read_csv(file_path)
        return df.fillna(0).to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading daily report: {str(e)}")

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

@app.post("/upload_data")
async def upload_data(username: str, files: List[UploadFile] = File(...)):
    """Endpoint to upload multiple supply chain data files to a user's workspace."""
    workspace_dir = os.path.join("dataset", "workspaces", username)
    os.makedirs(workspace_dir, exist_ok=True)
    
    saved_files = []
    
    try:
        for file in files:
            file_location = os.path.join(workspace_dir, file.filename)
            
            # Read and check size
            content = await file.read()
            if len(content) > MAX_FILE_SIZE:
                 raise HTTPException(status_code=413, detail=f"File {file.filename} exceeds the 50MB size limit.")
            
            # Reset file pointer for writing (or just write content)
            with open(file_location, "wb") as buffer:
                buffer.write(content)
            
            saved_files.append(file.filename)
        
        # Trigger the advanced processing pipeline
        from backend.data_processor import process_uploaded_data
        process_uploaded_data(username)
        
        return {
            "message": f"Successfully uploaded {len(saved_files)} files and triggered processing for {username}",
            "files": saved_files,
            "workspace": username
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading or processing files: {str(e)}")

@app.get("/workspace_files")
def get_workspace_files(username: str):
    """Returns a list of files in the user's workspace with metadata."""
    meta_path = os.path.join(PROCESSED_DATA_DIR, "workspace_metadata.csv")
    if not os.path.exists(meta_path):
        return []
    try:
        df = pd.read_csv(meta_path)
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading workspace metadata: {str(e)}")

@app.get("/data_explorer")
def get_data_explorer(username: str, filename: str):
    """Returns the content of a specific file in the workspace for preview."""
    workspace_dir = os.path.join("dataset", "workspaces", username)
    file_path = os.path.join(workspace_dir, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    try:
        # Load first 1000 rows for preview
        if filename.endswith('.csv'):
            df = pd.read_csv(file_path).head(1000)
        elif filename.endswith('.xlsx'):
            df = pd.read_excel(file_path).head(1000)
        elif filename.endswith('.json'):
            df = pd.read_json(file_path).head(1000)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")
            
        return df.fillna("").to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file {filename}: {str(e)}")

@app.get("/admin/system_health")
def get_system_health():
    """Returns administrative system health metrics."""
    return {
        "status": "Healthy",
        "api_version": "1.0.0",
        "workspaces": len(os.listdir("dataset/workspaces")) if os.path.exists("dataset/workspaces") else 0,
        "processed_files": len(os.listdir(PROCESSED_DATA_DIR)) if os.path.exists(PROCESSED_DATA_DIR) else 0,
        "storage_usage_mb": 142.5 # Mock value for now
    }

@app.post("/admin/clear_workspace")
def clear_workspace(username: str):
    """Administrative action to clear a user's workspace data."""
    workspace_dir = os.path.join("dataset", "workspaces", username)
    if os.path.exists(workspace_dir):
        shutil.rmtree(workspace_dir)
        os.makedirs(workspace_dir, exist_ok=True)
        return {"message": f"Workspace {username} cleared successfully"}
    return {"message": "Workspace not found"}

if __name__ == "__main__":
    import uvicorn
    # In a real scenario, you'd use host="0.0.0.0" for external access
    uvicorn.run(app, host="127.0.0.1", port=8000)
