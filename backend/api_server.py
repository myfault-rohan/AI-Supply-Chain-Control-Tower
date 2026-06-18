"""
backend/api_server.py
=====================
FastAPI backend serving the Olist Seller Churn predictive model results.
"""

import os
import sys
import pandas as pd
import numpy as np
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")
MODELS_DIR = os.path.join(PROJECT_ROOT, "data", "models")

# Global variables to cache data in memory
api_data = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the scored test data and SHAP values into memory on startup."""
    scored_path = os.path.join(PROCESSED_DIR, "test_scored.parquet")
    shap_path = os.path.join(MODELS_DIR, "test_shap_values.npy")
    
    if os.path.exists(scored_path) and os.path.exists(shap_path):
        df = pd.read_parquet(scored_path)
        shap_vals = np.load(shap_path)
        
        # Sort by churn probability descending
        df = df.sort_values("churn_probability", ascending=False).reset_index(drop=True)
        
        # We need the top N high risk sellers
        # To align SHAP values, we need to map the sorted rows back to original indices
        # But wait, test_scored.parquet has the same order as test_shap_values.npy originally.
        # Let's rebuild the index mappings.
        df_orig = pd.read_parquet(scored_path)
        
        # Build a list of dicts for the API
        records = []
        features = [c for c in df_orig.columns if c not in ["seller_id", "seller_state", "observation_date", "churned", "churn_probability", "risk_tier"]]
        
        for idx in range(len(df_orig)):
            row = df_orig.iloc[idx]
            sv = shap_vals[idx]
            
            # Identify top 3 risk drivers (features pushing the prediction highest)
            top_indices = np.argsort(-sv)[:3]
            top_drivers = [
                {"feature": features[i], "value": float(row[features[i]]), "shap_impact": float(sv[i])}
                for i in top_indices if sv[i] > 0
            ]
            
            records.append({
                "seller_id": str(row["seller_id"]),
                "seller_state": str(row["seller_state"]),
                "churn_probability": float(row["churn_probability"]),
                "risk_tier": str(row["risk_tier"]),
                "revenue_at_risk": float(row["revenue_at_risk_30d"]),
                "actual_churn": bool(row["churned"]),
                "metrics": {
                    "orders_30d": float(row["orders_30d"]),
                    "otd_rate": float(row["rolling_30d_otd_rate"]),
                    "review_score": float(row["rolling_30d_avg_review"]),
                    "dispatch_delay_slope": float(row["dispatch_delay_slope"])
                },
                "top_drivers": top_drivers
            })
            
        # Sort records by probability descending
        records.sort(key=lambda x: x["churn_probability"], reverse=True)
        api_data["sellers"] = records
        print(f"Loaded {len(records)} seller profiles into memory.")
    else:
        print("WARNING: Model artifacts not found. Run model training first.")
        api_data["sellers"] = []
        
    yield
    api_data.clear()

app = FastAPI(
    title="Olist Seller Risk API",
    description="Serves predictions from the XGBoost seller churn model.",
    version="3.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/api/v1/health")
def health_check():
    return {"status": "ok", "sellers_loaded": len(api_data.get("sellers", []))}

@app.get("/api/v1/seller-risk")
def get_seller_risk(limit: int = 100, tier: str = None):
    """
    Returns seller risk profiles including top SHAP drivers.
    Optionally filter by risk_tier (CRITICAL, WARNING, GOOD).
    """
    data = api_data.get("sellers", [])
    
    if tier:
        data = [s for s in data if s["risk_tier"] == tier.upper()]
        
    return data[:limit]

@app.get("/api/v1/seller-risk/{seller_id}")
def get_single_seller(seller_id: str):
    data = api_data.get("sellers", [])
    for s in data:
        if s["seller_id"] == seller_id:
            return s
    raise HTTPException(status_code=404, detail="Seller not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
