# -*- coding: utf-8 -*-
"""
Pandas-based Supply Chain Processing Pipeline
Replaces the PySpark dependency entirely.
Reads uploaded CSVs and generates ALL processed output files.
"""

import os
import sys
import shutil
import pandas as pd
import numpy as np
from datetime import datetime

# Add project root to path for config import
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import DATASET_DIR

PROCESSED_DIR = os.path.join(DATASET_DIR, "processed files")
os.makedirs(PROCESSED_DIR, exist_ok=True)

DATA_TYPE_MAP = {
    "inventory":  ["product_id", "current_stock", "safety_stock"],
    "sales":      ["product_id", "daily_sales"],
    "suppliers":  ["supplier_id", "lead_time_days"],
    "shipments":  ["shipment_id", "supplier_id", "product_id", "actual_delivery"],
    "warehouses": ["warehouse_id", "capacity"],
}

HOLDING_COST_PER_UNIT = 2.0
STOCKOUT_COST_PER_UNIT = 5.0

def _detect_type(df):
    headers = [c.strip().lower() for c in df.columns]
    for dtype, required in DATA_TYPE_MAP.items():
        if all(col in headers for col in required):
            return dtype
    time_cols = {"date", "timestamp", "time", "year", "month"}
    val_cols  = {"amount", "value", "price", "revenue", "cost", "sales"}
    if time_cols & set(headers) and val_cols & set(headers):
        return "timeseries"
    geo_cols = {"country", "city", "latitude", "longitude", "lat", "lon"}
    if geo_cols & set(headers):
        return "geospatial"
    return "generic"

def _norm_cols(df):
    df.columns = [c.strip().lower() for c in df.columns]
    return df

def _safe_read(path):
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".xlsx":
            return _norm_cols(pd.read_excel(path))
        if ext == ".json":
            return _norm_cols(pd.read_json(path))
        return _norm_cols(pd.read_csv(path))
    except Exception as e:
        print(f"  [WARN] Could not read {path}: {e}")
        return pd.DataFrame()

def load_workspace_files(workspace_dir):
    buckets = {k: None for k in DATA_TYPE_MAP}
    buckets["generic"] = []
    metadata = []
    for fname in os.listdir(workspace_dir):
        if not fname.endswith((".csv", ".xlsx", ".json")):
            continue
        fpath = os.path.join(workspace_dir, fname)
        df = _safe_read(fpath)
        if df.empty:
            continue
        dtype = _detect_type(df)
        rows, cols = df.shape
        metadata.append({"filename": fname, "type": dtype, "rows": rows, "cols": cols})
        if dtype in DATA_TYPE_MAP:
            buckets[dtype] = df
            df.to_csv(os.path.join(DATASET_DIR, f"{dtype}.csv"), index=False)
            if dtype in ("inventory", "sales", "suppliers", "shipments"):
                df.to_csv(os.path.join(DATASET_DIR, f"stream_{dtype}.csv"), index=False)
        else:
            buckets["generic"].append(df)
    pd.DataFrame(metadata).to_csv(
        os.path.join(PROCESSED_DIR, "workspace_metadata.csv"), index=False)
    return buckets

def build_processed_supply_chain(buckets):
    inv = buckets.get("inventory")
    sal = buckets.get("sales")
    shp = buckets.get("shipments")
    if inv is None:
        print("  [SKIP] No inventory data.")
        return pd.DataFrame()
    if sal is not None and "daily_sales" in sal.columns:
        avg_sales = sal.groupby("product_id")["daily_sales"].mean().reset_index()
        avg_sales.rename(columns={"daily_sales": "avg_daily_sales"}, inplace=True)
    elif "daily_demand" in inv.columns:
        avg_sales = inv[["product_id","daily_demand"]].rename(
            columns={"daily_demand":"avg_daily_sales"})
    else:
        avg_sales = pd.DataFrame({
            "product_id": inv["product_id"],
            "avg_daily_sales": np.random.uniform(50, 500, len(inv)).round(1)})
    if shp is not None and "actual_delivery" in shp.columns and "expected_delivery" in shp.columns:
        shp = shp.copy()
        shp["actual_delivery"]   = pd.to_datetime(shp["actual_delivery"],   errors="coerce")
        shp["expected_delivery"] = pd.to_datetime(shp["expected_delivery"], errors="coerce")
        shp["delay_days"] = (shp["actual_delivery"]-shp["expected_delivery"]).dt.days.clip(lower=0)
        avg_delay = shp.groupby("product_id")["delay_days"].mean().reset_index()
        avg_delay.rename(columns={"delay_days":"avg_delay_days"}, inplace=True)
    else:
        avg_delay = pd.DataFrame({
            "product_id": inv["product_id"],
            "avg_delay_days": np.random.uniform(0, 5, len(inv)).round(1)})
    df = inv.copy().merge(avg_sales, on="product_id", how="left").merge(
        avg_delay, on="product_id", how="left")
    for col in ("safety_stock", "reorder_point"):
        if col not in df.columns:
            df[col] = (df["current_stock"] * 0.2).round(0)
    if "warehouse_id" not in df.columns:
        df["warehouse_id"] = "W1"
    df["avg_daily_sales"] = df["avg_daily_sales"].fillna(df["current_stock"]/30).clip(lower=1)
    df["avg_delay_days"]  = df["avg_delay_days"].fillna(3)
    df["inventory_days"]  = (df["current_stock"] / df["avg_daily_sales"]).round(2)
    df.to_csv(os.path.join(DATASET_DIR, "processed_supply_chain.csv"), index=False)
    print(f"  ✅ processed_supply_chain.csv → {len(df)} rows")
    return df

def build_demand_predictions(df_sc):
    if df_sc.empty:
        return pd.DataFrame()
    df = df_sc.copy()
    df["predicted_demand"] = (
        df["avg_daily_sales"] * 1.05 +
        np.random.normal(0, df["avg_daily_sales"] * 0.05, len(df))
    ).clip(lower=0.1).round(2)
    df["demand_spike"]        = df["predicted_demand"] > df["avg_daily_sales"] * 1.3
    df["days_until_stockout"] = (df["current_stock"] / df["predicted_demand"]).round(2)
    df.to_csv(os.path.join(DATASET_DIR, "demand_predictions.csv"), index=False)
    print(f"  ✅ demand_predictions.csv → {len(df)} rows")
    return df

def build_reorder_recommendations(df_demand, buckets):
    if df_demand.empty:
        return pd.DataFrame()
    df = df_demand.copy()
    sup = buckets.get("suppliers")
    shp = buckets.get("shipments")
    if shp is not None and sup is not None and "supplier_id" in shp.columns:
        merged = shp.merge(sup[["supplier_id","lead_time_days"]], on="supplier_id", how="left")
        lt = merged.groupby("product_id")["lead_time_days"].mean().reset_index()
        lt.rename(columns={"lead_time_days":"supplier_lead_time"}, inplace=True)
        df = df.merge(lt, on="product_id", how="left")
    if "supplier_lead_time" not in df.columns:
        df["supplier_lead_time"] = 7.0
    df["supplier_lead_time"] = df["supplier_lead_time"].fillna(7.0)
    df["reorder_quantity"] = (
        df["predicted_demand"] * df["supplier_lead_time"]
        + df["safety_stock"] - df["current_stock"]
    ).clip(lower=0).round(0)
    df["stockout_risk"] = df["days_until_stockout"] < df["supplier_lead_time"]
    def make_alert(row):
        if row["days_until_stockout"] < 3:
            return f"CRITICAL: {row['product_id']} stockout in {row['days_until_stockout']:.1f} days!"
        if row["stockout_risk"]:
            return f"WARNING: Reorder {row['product_id']} - {row['days_until_stockout']:.1f} days left."
        return f"OK: {row['product_id']} has sufficient stock."
    df["alert_message"] = df.apply(make_alert, axis=1)
    out = df[["product_id","current_stock","predicted_demand","days_until_stockout",
              "reorder_quantity","supplier_lead_time","stockout_risk","alert_message"]]
    out.to_csv(os.path.join(PROCESSED_DIR, "reorder_recommendations.csv"), index=False)
    print(f"  ✅ reorder_recommendations.csv → {len(out)} rows")
    return out

def build_health_scores(df_reorder):
    if df_reorder.empty:
        return pd.DataFrame()
    def score(days):
        if days < 3:  return "CRITICAL", 20
        if days <= 7: return "WARNING",  60
        return "GOOD", 100
    df = df_reorder.copy()
    df[["health_status","health_score"]] = df["days_until_stockout"].apply(
        lambda d: pd.Series(score(d)))
    out = df[["product_id","current_stock","predicted_demand",
              "days_until_stockout","reorder_quantity","health_status","health_score"]]
    out.to_csv(os.path.join(PROCESSED_DIR, "supply_chain_health.csv"), index=False)
    print(f"  ✅ supply_chain_health.csv → {len(out)} rows")
    return out

def build_supplier_performance(buckets):
    shp = buckets.get("shipments")
    sup = buckets.get("suppliers")
    if shp is None:
        return pd.DataFrame()
    df = shp.copy()
    if "actual_delivery" in df.columns and "expected_delivery" in df.columns:
        df["actual_delivery"]   = pd.to_datetime(df["actual_delivery"],   errors="coerce")
        df["expected_delivery"] = pd.to_datetime(df["expected_delivery"], errors="coerce")
        df["delay_days"] = (df["actual_delivery"]-df["expected_delivery"]).dt.days.fillna(0).clip(lower=0)
    else:
        df["delay_days"] = 0
    metrics = df.groupby("supplier_id").agg(
        average_delay    =("delay_days",  "mean"),
        total_shipments  =("shipment_id", "count"),
        on_time_shipments=("delay_days",  lambda x: (x <= 0).sum()),
    ).reset_index()
    metrics["reliability_score"] = (
        metrics["on_time_shipments"]/metrics["total_shipments"]*100).round(1)
    metrics["delay_rate"] = (100 - metrics["reliability_score"]).round(1)
    metrics["supplier_status"] = metrics["reliability_score"].apply(
        lambda s: "GOOD" if s > 85 else ("WARNING" if s >= 60 else "CRITICAL"))
    if sup is not None and "supplier_name" in sup.columns:
        metrics = metrics.merge(sup[["supplier_id","supplier_name"]], on="supplier_id", how="left")
    metrics.to_csv(os.path.join(PROCESSED_DIR, "supplier_performance.csv"), index=False)
    print(f"  ✅ supplier_performance.csv → {len(metrics)} rows")
    return metrics

def build_warehouse_utilisation(buckets):
    inv  = buckets.get("inventory")
    ware = buckets.get("warehouses")
    if inv is None or ware is None:
        return pd.DataFrame()
    stock = inv.groupby("warehouse_id")["current_stock"].sum().reset_index()
    stock.rename(columns={"current_stock":"total_stock"}, inplace=True)
    df = ware.merge(stock, on="warehouse_id", how="left")
    df["total_stock"] = df["total_stock"].fillna(0)
    df["utilization_percent"] = (df["total_stock"]/df["capacity"]*100).round(1)
    df["status"] = df["utilization_percent"].apply(
        lambda p: "HIGH" if p > 85 else ("NORMAL" if p >= 40 else "LOW"))
    df.to_csv(os.path.join(PROCESSED_DIR, "warehouse_utilization.csv"), index=False)
    print(f"  ✅ warehouse_utilization.csv → {len(df)} rows")
    return df

def build_cost_analytics(df_demand):
    if df_demand.empty:
        return pd.DataFrame()
    df = df_demand.copy()
    df["inventory_holding_cost"] = df["current_stock"] * HOLDING_COST_PER_UNIT
    df["stockout_cost"] = df.apply(
        lambda r: r["predicted_demand"] * STOCKOUT_COST_PER_UNIT
        if r["days_until_stockout"] < 5 else 0, axis=1)
    df["total_cost_impact"] = df["inventory_holding_cost"] + df["stockout_cost"]
    out = df[["product_id","inventory_holding_cost","stockout_cost","total_cost_impact"]]
    out.to_csv(os.path.join(PROCESSED_DIR, "cost_analysis.csv"), index=False)
    print(f"  ✅ cost_analysis.csv → {len(out)} rows")
    return out

def build_global_risk_summary(health_df, supplier_df, warehouse_df, cost_df):
    summary = pd.DataFrame([{
        "critical_products":     int((health_df["health_status"]=="CRITICAL").sum())    if not health_df.empty    else 0,
        "unreliable_suppliers":  int((supplier_df["supplier_status"]=="CRITICAL").sum()) if not supplier_df.empty else 0,
        "overloaded_warehouses": int((warehouse_df["status"]=="HIGH").sum())             if not warehouse_df.empty else 0,
        "high_cost_products":    int((cost_df["total_cost_impact"]>500).sum())           if not cost_df.empty     else 0,
        "generated_at":          datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }])
    summary.to_csv(os.path.join(PROCESSED_DIR, "global_risk_summary.csv"), index=False)
    summary.to_csv(os.path.join(DATASET_DIR,   "global_risk_summary.csv"), index=False)
    print("  ✅ global_risk_summary.csv saved")
    return summary

def run_full_pipeline(username="default"):
    workspace_dir = os.path.join(DATASET_DIR, "workspaces", username)
    if not os.path.exists(workspace_dir):
        return {"success": False, "error": f"Workspace '{username}' not found."}
    print(f"\n{'='*55}\n  Pandas Pipeline — user: {username}\n{'='*55}")
    buckets = load_workspace_files(workspace_dir)
    if buckets.get("inventory") is None:
        inv_fallback = os.path.join(DATASET_DIR, "inventory.csv")
        if os.path.exists(inv_fallback):
            buckets["inventory"] = _norm_cols(pd.read_csv(inv_fallback))
    if buckets.get("inventory") is None:
        return {"success": False, "error": "No inventory file found. Upload inventory.csv"}
    df_sc      = build_processed_supply_chain(buckets)
    df_demand  = build_demand_predictions(df_sc)
    df_reorder = build_reorder_recommendations(df_demand, buckets)
    df_health  = build_health_scores(df_reorder)
    df_sup     = build_supplier_performance(buckets)
    df_ware    = build_warehouse_utilisation(buckets)
    df_cost    = build_cost_analytics(df_demand)
    build_global_risk_summary(df_health, df_sup, df_ware, df_cost)
    print(f"{'='*55}\n  Pipeline complete!\n{'='*55}\n")
    return {
        "success": True,
        "rows_processed": len(df_sc),
        "products":        int(df_sc["product_id"].nunique()) if not df_sc.empty else 0,
        "critical_alerts": int((df_health["health_status"]=="CRITICAL").sum()) if not df_health.empty else 0,
        "warnings":        int((df_health["health_status"]=="WARNING").sum())  if not df_health.empty else 0,
        "cost_exposure":   float(df_cost["total_cost_impact"].sum())            if not df_cost.empty  else 0.0,
    }

if __name__ == "__main__":
    import sys
    result = run_full_pipeline(sys.argv[1] if len(sys.argv) > 1 else "default")
    print(result)
