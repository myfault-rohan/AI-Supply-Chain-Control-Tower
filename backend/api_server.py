"""
AI Supply Chain Control Tower — FastAPI Backend
Enterprise-grade REST API with JWT authentication, CORS support,
comprehensive OpenAPI documentation, and data-quality endpoints.
"""

import os
import sys
import shutil
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import API_URL, DATASET_DIR
PROCESSED_DATA_DIR = os.path.join(DATASET_DIR, "processed files")
APP_VERSION = "2.0.0"
APP_TITLE = "AI Supply Chain Control Tower API"
API_HOST = "127.0.0.1"
API_PORT = 8000

from backend.auth import authenticate_user, create_access_token, verify_token
from backend.database import get_db
from backend.schemas import (
    HealthCheck, TokenRequest, TokenResponse, UploadResponse,
    SystemHealth, DataQualityReport
)

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("api")

# FastAPI App
app = FastAPI(
    title=APP_TITLE,
    description=(
        "Enterprise REST API for real-time supply chain monitoring, "
        "ML-powered demand forecasting, and AI-driven risk analysis. "
        "Built with FastAPI, XGBoost, and Pandas."
    ),
    version=APP_VERSION,
    contact={"name": "Supply Chain AI Team", "email": "support@example.com"},
    license_info={"name": "MIT"},
)

# Rate Limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Middleware
app.add_middleware(CORSMiddleware,
    allow_origins=["http://localhost:8501","http://127.0.0.1:8501"],
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"]
)

# Security
security = HTTPBearer(auto_error=False)

# File Paths
DEMAND_FILE = os.path.join(PROCESSED_DATA_DIR, 'demand_predictions.csv')
REORDER_FILE = os.path.join(PROCESSED_DATA_DIR, 'reorder_recommendations.csv')
HEALTH_FILE = os.path.join(PROCESSED_DATA_DIR, 'supply_chain_health.csv')
UPLOAD_DIR = os.path.join(DATASET_DIR, 'uploads')

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


# --- Auth Dependency ---
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Validate JWT token and return username. Returns None if no token provided."""
    if credentials is None:
        return None
    try:
        payload = verify_token(credentials.credentials)
        return payload.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


async def require_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Require valid JWT token. Raises 401 if missing or invalid."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = verify_token(credentials.credentials)
        return payload.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# --- Security Helpers ---
import re

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal attacks."""
    # Remove path separators and null bytes
    name = os.path.basename(filename)
    # Remove any remaining dangerous characters
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)
    # Prevent hidden files
    name = name.lstrip('.')
    if not name:
        raise HTTPException(status_code=400, detail="Invalid filename")
    return name


def validate_workspace_path(base_dir: str, file_path: str) -> str:
    """Validate that file_path stays within base_dir."""
    abs_base = os.path.abspath(base_dir)
    abs_path = os.path.abspath(file_path)
    if not abs_path.startswith(abs_base + os.sep):
        raise HTTPException(status_code=400, detail="Invalid file path")
    return abs_path


# --- Helper ---
def load_dataset(filepath: str) -> pd.DataFrame:
    """Load a CSV dataset, raising 404 if not found."""
    if not os.path.exists(filepath):
        raise HTTPException(
            status_code=404,
            detail=f"Dataset not found: {os.path.basename(filepath)}. Please upload data first."
        )
    return pd.read_csv(filepath)


# ═══════════════════════════════════════════════════
#            AUTHENTICATION ENDPOINTS
# ═══════════════════════════════════════════════════

@app.post("/api/v1/token", response_model=TokenResponse, tags=["Authentication"],
          summary="Authenticate and receive JWT token")
@limiter.limit("5/minute")
async def login(request: Request, form: TokenRequest, db: Session = Depends(get_db)):
    """
    Authenticate with username and password.
    Returns a JWT bearer token valid for 8 hours.
    """
    user = authenticate_user(db, form.username, form.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token({"sub": form.username})
    logger.info(f"User '{form.username}' authenticated successfully")
    return TokenResponse(access_token=token, token_type="bearer", username=form.username)


# ═══════════════════════════════════════════════════
#              SYSTEM ENDPOINTS
# ═══════════════════════════════════════════════════

@app.get("/", tags=["System"])
@limiter.limit("60/minute")
def read_root(request: Request):
    """Root endpoint with API information."""
    return {
        "message": "AI Supply Chain Control Tower API",
        "version": APP_VERSION,
        "docs": "/docs",
        "health": "/api/v1/health",
    }

@app.get("/api/v1/health", response_model=HealthCheck, tags=["System"],
         summary="Health check for Docker and monitoring")
def health_check():
    """Returns API health status, version, and current timestamp."""
    return HealthCheck(
        status="ok",
        version=APP_VERSION,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


# ═══════════════════════════════════════════════════
#           SUPPLY CHAIN DATA ENDPOINTS
# ═══════════════════════════════════════════════════

@app.get("/inventory", response_model=List[Dict], tags=["Supply Chain"],
         summary="Get current inventory status")
def get_inventory():
    """Returns the current inventory status for all products including stock levels and days coverage."""
    df = load_dataset(DEMAND_FILE)
    inventory_cols = ['product_id', 'warehouse_id', 'current_stock', 'safety_stock', 'reorder_point', 'inventory_days']
    available_cols = [c for c in inventory_cols if c in df.columns]
    return df[available_cols].fillna(0).to_dict(orient='records')


@app.get("/demand_forecast", response_model=List[Dict], tags=["Supply Chain"],
         summary="Get ML demand predictions")
def get_demand_forecast():
    """Returns XGBoost-predicted demand for all products with spike detection."""
    df = load_dataset(DEMAND_FILE)
    forecast_cols = ['product_id', 'predicted_demand', 'avg_daily_sales', 'demand_spike']
    available_cols = [c for c in forecast_cols if c in df.columns]
    return df[available_cols].fillna(0).to_dict(orient='records')


@app.get("/reorder_recommendations", response_model=List[Dict], tags=["Supply Chain"],
         summary="Get reorder recommendations")
def get_reorder_recommendations():
    """Returns reorder recommendations including quantities, lead times, and alert messages."""
    df = load_dataset(REORDER_FILE)
    cols = ['product_id', 'reorder_quantity', 'supplier_lead_time', 'alert_message']
    available_cols = [c for c in cols if c in df.columns]
    return df[available_cols].fillna(0).to_dict(orient='records')


@app.get("/alerts", response_model=List[Dict], tags=["Alerts"],
         summary="Get urgent supply chain alerts")
def get_alerts():
    """Returns urgent supply chain alerts for products at high risk of stockout."""
    df = load_dataset(REORDER_FILE)
    alerts_df = df[df['stockout_risk'] == True]
    cols = ['product_id', 'days_until_stockout', 'alert_message']
    available_cols = [c for c in cols if c in df.columns]
    return alerts_df[available_cols].to_dict(orient='records')


@app.get("/health", response_model=List[Dict], tags=["Supply Chain"],
         summary="Get supply chain health metrics")
def get_health():
    """Returns health scores and status (GOOD/WARNING/CRITICAL) for all products."""
    df = load_dataset(HEALTH_FILE)
    return df.fillna(0).to_dict(orient='records')


@app.get("/live_inventory", response_model=List[Dict], tags=["Supply Chain"],
         summary="Get live streaming inventory data")
def get_live_inventory():
    """Returns the latest entries from the live streaming supply chain data directory."""
    live_dir = os.path.join(DATASET_DIR, 'live_supply_chain')
    if not os.path.exists(live_dir) or not os.path.isdir(live_dir):
        raise HTTPException(
            status_code=404,
            detail="Live streaming data directory not found. Ensure the Spark streaming processor is running."
        )
    
    try:
        files = [os.path.join(live_dir, f) for f in os.listdir(live_dir) if f.endswith('.csv')]
        if not files:
            return []
        
        dfs = [pd.read_csv(f) for f in files]
        if not dfs:
            return []
        
        combined_df = pd.concat(dfs, ignore_index=True)
        return combined_df.tail(100).to_dict(orient='records')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading live data: {str(e)}")


@app.get("/live_alerts", response_model=List[Dict], tags=["Alerts"],
         summary="Get live monitoring alerts")
def get_live_alerts():
    """Returns the latest alerts from the supply chain monitoring system."""
    file_path = os.path.join(DATASET_DIR, "live_alerts.csv")
    if not os.path.exists(file_path):
        return []
    try:
        df = pd.read_csv(file_path)
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading alerts data: {str(e)}")


# ═══════════════════════════════════════════════════
#         ANALYTICS & PERFORMANCE ENDPOINTS
# ═══════════════════════════════════════════════════

@app.get("/supplier_performance", response_model=List[Dict], tags=["Analytics"],
         summary="Get supplier reliability metrics")
def get_supplier_performance():
    """Returns supplier performance metrics including reliability scores and delay rates."""
    file_path = os.path.join(PROCESSED_DATA_DIR, "supplier_performance.csv")
    if not os.path.exists(file_path):
        return []
    try:
        df = pd.read_csv(file_path)
        return df.fillna(0).to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading supplier performance data: {str(e)}")


@app.get("/warehouse_utilization", response_model=List[Dict], tags=["Analytics"],
         summary="Get warehouse capacity utilization")
def get_warehouse_utilization():
    """Returns warehouse utilization percentages and status classifications."""
    file_path = os.path.join(PROCESSED_DATA_DIR, "warehouse_utilization.csv")
    if not os.path.exists(file_path):
        return []
    try:
        df = pd.read_csv(file_path)
        return df.fillna(0).to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading warehouse utilization data: {str(e)}")


@app.get("/cost_analysis", response_model=List[Dict], tags=["Analytics"],
         summary="Get cost impact analysis")
def get_cost_analysis():
    """Returns holding costs, stockout costs, and total financial impact per product."""
    file_path = os.path.join(PROCESSED_DATA_DIR, "cost_analysis.csv")
    if not os.path.exists(file_path):
        return []
    try:
        df = pd.read_csv(file_path)
        return df.fillna(0).to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading cost analysis data: {str(e)}")


@app.get("/global_risk_summary", response_model=List[Dict], tags=["Analytics"],
         summary="Get aggregated risk overview")
def get_global_risk_summary():
    """Returns aggregated global risk summary with counts of critical items across all dimensions."""
    file_path = os.path.join(PROCESSED_DATA_DIR, "global_risk_summary.csv")
    if not os.path.exists(file_path):
        return []
    try:
        df = pd.read_csv(file_path)
        return df.fillna(0).to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading global risk summary: {str(e)}")


@app.get("/daily_report", response_model=List[Dict], tags=["Reports"],
         summary="Get latest daily report")
def get_daily_report():
    """Returns the latest daily supply chain risk report summary."""
    file_path = os.path.join(PROJECT_ROOT, "reports", "daily_supply_chain_report.csv")
    if not os.path.exists(file_path):
        return []
    try:
        df = pd.read_csv(file_path)
        return df.fillna(0).to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading daily report: {str(e)}")


@app.get("/export/pdf", tags=["Reports"], summary="Download executive PDF report")
def export_pdf(current_user: str = Depends(require_auth)):
    """Generate and download a professional executive PDF report. Requires authentication."""
    from fastapi.responses import FileResponse
    try:
        from reporting.daily_report_generator import generate_pdf_report
        pdf_path = generate_pdf_report()
        if pdf_path and os.path.exists(pdf_path):
            return FileResponse(
                pdf_path,
                media_type="application/pdf",
                filename=f"executive_report_{datetime.now().strftime('%Y%m%d')}.pdf"
            )
        raise HTTPException(status_code=500, detail="PDF generation failed")
    except ImportError:
        raise HTTPException(status_code=500, detail="reportlab not installed. Run: pip install reportlab")


# ═══════════════════════════════════════════════════
#          DATA MANAGEMENT ENDPOINTS
# ═══════════════════════════════════════════════════

@app.post("/upload_data", response_model=UploadResponse, tags=["Data Management"],
          summary="Upload supply chain data files")
@limiter.limit("10/minute")
async def upload_data(
    request: Request,
    files: List[UploadFile] = File(...),
    current_user: str = Depends(require_auth)
):
    """
    Upload multiple supply chain data files (CSV, Excel, JSON) to your workspace.
    Files are automatically classified and trigger the analytics pipeline.
    Maximum file size: 50MB per file. Requires authentication.
    """
    username = current_user
    workspace_dir = os.path.join(DATASET_DIR, "workspaces", username)
    os.makedirs(workspace_dir, exist_ok=True)

    saved_files = []

    try:
        for file in files:
            # Sanitize filename to prevent path traversal
            safe_filename = sanitize_filename(file.filename)
            file_location = os.path.join(workspace_dir, safe_filename)
            validate_workspace_path(workspace_dir, file_location)

            content = await file.read()
            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(status_code=413, detail=f"File {safe_filename} exceeds the 50MB size limit.")

            with open(file_location, "wb") as buffer:
                buffer.write(content)

            saved_files.append(safe_filename)
            logger.info(f"Uploaded {safe_filename} for user '{username}'")

        # Trigger the pandas pipeline (no Spark needed)
        from backend.pandas_processor import run_full_pipeline
        result = run_full_pipeline(username)
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error","Pipeline failed"))

        return UploadResponse(
            message=f"Successfully uploaded {len(saved_files)} files and triggered processing for {username}",
            files=saved_files,
            workspace=username
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error uploading or processing files: {str(e)}")


@app.get("/workspace_files", response_model=List[Dict], tags=["Data Management"],
         summary="List workspace files with metadata")
def get_workspace_files(current_user: str = Depends(require_auth)):
    """Returns a list of files in your workspace with type detection metadata. Requires authentication."""
    meta_path = os.path.join(PROCESSED_DATA_DIR, "workspace_metadata.csv")
    if not os.path.exists(meta_path):
        return []
    try:
        df = pd.read_csv(meta_path)
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading workspace metadata: {str(e)}")


@app.get("/data_explorer", response_model=List[Dict], tags=["Data Management"],
         summary="Preview a workspace file")
def get_data_explorer(filename: str = Query(...), current_user: str = Depends(require_auth)):
    """Returns the first 1000 rows of a specific file for data preview. Requires authentication."""
    # Sanitize filename to prevent path traversal
    safe_filename = sanitize_filename(filename)
    workspace_dir = os.path.join(DATASET_DIR, "workspaces", current_user)
    file_path = os.path.join(workspace_dir, safe_filename)
    validate_workspace_path(workspace_dir, file_path)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    try:
        if safe_filename.endswith('.csv'):
            df = pd.read_csv(file_path).head(1000)
        elif safe_filename.endswith('.xlsx'):
            df = pd.read_excel(file_path).head(1000)
        elif safe_filename.endswith('.json'):
            df = pd.read_json(file_path).head(1000)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")

        return df.fillna("").to_dict(orient="records")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")


# ═══════════════════════════════════════════════════
#          DATA QUALITY ENDPOINT
# ═══════════════════════════════════════════════════

@app.get("/data-quality", response_model=List[Dict], tags=["Data Management"],
         summary="Get data quality analysis")
def get_data_quality(current_user: str = Depends(require_auth)):
    """Returns data quality analysis for all files in your workspace. Requires authentication."""
    workspace_dir = os.path.join(DATASET_DIR, "workspaces", current_user)
    if not os.path.exists(workspace_dir):
        return []
    
    reports = []
    for filename in os.listdir(workspace_dir):
        if not filename.endswith(('.csv', '.xlsx', '.json')):
            continue
        
        file_path = os.path.join(workspace_dir, filename)
        try:
            if filename.endswith('.csv'):
                df = pd.read_csv(file_path)
            elif filename.endswith('.xlsx'):
                df = pd.read_excel(file_path)
            else:
                df = pd.read_json(file_path)
            
            null_counts = df.isnull().sum().to_dict()
            null_pcts = {k: round(v / len(df) * 100, 1) for k, v in null_counts.items()} if len(df) > 0 else {}
            duplicate_rows = int(df.duplicated().sum())
            
            # Quality score
            total_cells = df.shape[0] * df.shape[1]
            null_cells = sum(null_counts.values())
            completeness = (1 - null_cells / total_cells) * 100 if total_cells > 0 else 100
            uniqueness = (1 - duplicate_rows / len(df)) * 100 if len(df) > 0 else 100
            quality_score = round((completeness * 0.7 + uniqueness * 0.3), 1)
            
            # Issues
            issues = []
            for col, pct in null_pcts.items():
                if pct > 5:
                    issues.append(f"Column '{col}' has {pct}% null values — recommend fill with default")
            if duplicate_rows > 0:
                issues.append(f"{duplicate_rows} duplicate rows detected")
            
            # Value range checks
            for col in df.select_dtypes(include='number').columns:
                if (df[col] < 0).any():
                    issues.append(f"Column '{col}' contains negative values")
            
            reports.append({
                "filename": filename,
                "total_rows": len(df),
                "total_columns": len(df.columns),
                "columns": list(df.columns),
                "null_counts": null_counts,
                "null_percentages": null_pcts,
                "duplicate_rows": duplicate_rows,
                "quality_score": quality_score,
                "issues": issues
            })
        except Exception as e:
            reports.append({
                "filename": filename,
                "error": str(e),
                "quality_score": 0
            })
    
    return reports


# ═══════════════════════════════════════════════════
#          ADMIN ENDPOINTS
# ═══════════════════════════════════════════════════

@app.get("/admin/system_health", response_model=SystemHealth, tags=["Admin"],
         summary="Get system health metrics")
def get_system_health(current_user: str = Depends(require_auth)):
    """Returns administrative system health metrics. Requires authentication."""
    workspaces_dir = os.path.join(DATASET_DIR, "workspaces")
    return SystemHealth(
        status="Healthy",
        api_version=APP_VERSION,
        workspaces=len(os.listdir(workspaces_dir)) if os.path.exists(workspaces_dir) else 0,
        processed_files=len(os.listdir(PROCESSED_DATA_DIR)) if os.path.exists(PROCESSED_DATA_DIR) else 0,
        storage_usage_mb=round(sum(
            os.path.getsize(os.path.join(dirpath, filename))
            for dirpath, dirnames, filenames in os.walk(DATASET_DIR)
            for filename in filenames
        ) / (1024 * 1024), 2) if os.path.exists(DATASET_DIR) else 0
    )


@app.post("/admin/clear_workspace", tags=["Admin"],
          summary="Clear user workspace data")
def clear_workspace(current_user: str = Depends(require_auth)):
    """Administrative action to clear all files in your workspace. Requires authentication."""
    workspace_dir = os.path.join(DATASET_DIR, "workspaces", current_user)
    if os.path.exists(workspace_dir):
        shutil.rmtree(workspace_dir)
        os.makedirs(workspace_dir, exist_ok=True)
        logger.info(f"Workspace '{current_user}' cleared")
        return {"message": f"Workspace {current_user} cleared successfully"}
    return {"message": "Workspace not found"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT)
