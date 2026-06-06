#!/usr/bin/env python3
"""
Feature Engineering Pipeline
==============================
Transforms raw supply chain data into ML-ready features.

Key feature groups:
  - Demand features: rolling stats, lag features, seasonality
  - Supplier features: reliability scores, delay trends
  - Inventory features: stockout risk, carrying cost
  - Cost features: total landed cost, margin analysis

Output: data/processed/features.csv
"""

import pandas as pd
import numpy as np
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR       = os.path.join(ROOT, "data", "raw")
PROCESSED_DIR = os.path.join(ROOT, "data", "processed")
os.makedirs(PROCESSED_DIR, exist_ok=True)


def load_raw():
    sales      = pd.read_csv(os.path.join(RAW_DIR, "sales.csv"), parse_dates=["date"])
    inventory  = pd.read_csv(os.path.join(RAW_DIR, "inventory.csv"))
    products   = pd.read_csv(os.path.join(RAW_DIR, "products.csv"))
    suppliers  = pd.read_csv(os.path.join(RAW_DIR, "shipments.csv"), parse_dates=["order_date", "actual_date"])
    return sales, inventory, products, suppliers


def build_demand_features(sales: pd.DataFrame) -> pd.DataFrame:
    """Per-product daily features with lags and rolling stats."""
    print("  Building demand features...")
    df = sales.sort_values(["product_id", "date"]).copy()
    df = df.groupby("product_id").apply(lambda x: x.set_index("date")).drop(columns="product_id").reset_index()

    agg = []
    for pid, grp in df.groupby("product_id"):
        grp = grp.sort_values("date").copy()
        grp["lag_7"]  = grp["daily_sales"].shift(7)
        grp["lag_14"] = grp["daily_sales"].shift(14)
        grp["lag_30"] = grp["daily_sales"].shift(30)
        grp["roll_7_mean"]  = grp["daily_sales"].rolling(7).mean()
        grp["roll_30_mean"] = grp["daily_sales"].rolling(30).mean()
        grp["roll_7_std"]   = grp["daily_sales"].rolling(7).std()
        grp["roll_90_mean"] = grp["daily_sales"].rolling(90).mean()
        grp["mom_change"]   = grp["roll_30_mean"].pct_change(30)   # Month-over-month
        grp["yoy_change"]   = grp["daily_sales"].pct_change(365)   # Year-over-year
        grp["day_of_week"]  = grp["date"].dt.dayofweek
        grp["month"]        = grp["date"].dt.month
        grp["quarter"]      = grp["date"].dt.quarter
        grp["is_weekend"]   = (grp["day_of_week"] >= 5).astype(int)
        grp["is_month_end"] = grp["date"].dt.is_month_end.astype(int)
        agg.append(grp)

    return pd.concat(agg).reset_index(drop=True)


def build_supplier_features(shipments: pd.DataFrame) -> pd.DataFrame:
    """Aggregate supplier-level performance metrics."""
    print("  Building supplier features...")
    grp = shipments.groupby("supplier_id").agg(
        total_shipments     = ("shipment_id", "count"),
        avg_delay_days      = ("delay_days", "mean"),
        max_delay_days      = ("delay_days", "max"),
        on_time_rate        = ("on_time", "mean"),
        avg_defect_units    = ("defective_units", "mean"),
        total_spend         = ("total_cost", "sum"),
        avg_order_value     = ("total_cost", "mean"),
    ).reset_index()

    # Rolling 90-day reliability (recency-weighted)
    recent = shipments[shipments["order_date"] >= shipments["order_date"].max() - pd.Timedelta(days=90)]
    recent_rate = recent.groupby("supplier_id")["on_time"].mean().reset_index()
    recent_rate.columns = ["supplier_id", "recent_90d_on_time_rate"]
    grp = grp.merge(recent_rate, on="supplier_id", how="left")

    # Risk tier
    grp["supplier_risk_score"] = (
        (1 - grp["on_time_rate"]) * 0.5 +
        (grp["avg_delay_days"] / grp["avg_delay_days"].max()) * 0.3 +
        (grp["avg_defect_units"] / grp["avg_defect_units"].max()) * 0.2
    )
    grp["risk_tier"] = pd.cut(grp["supplier_risk_score"],
                               bins=[0, 0.2, 0.4, 1.0],
                               labels=["LOW", "MEDIUM", "HIGH"])
    return grp


def build_inventory_features(inventory: pd.DataFrame, demand_features: pd.DataFrame) -> pd.DataFrame:
    """Compute stockout probability and inventory health metrics."""
    print("  Building inventory features...")
    latest_demand = (
        demand_features
        .groupby("product_id")[["roll_30_mean", "roll_7_std"]]
        .last()
        .reset_index()
        .rename(columns={"roll_30_mean": "avg_demand_30d", "roll_7_std": "demand_std"})
    )

    inv = inventory.merge(latest_demand, on="product_id", how="left")
    inv["avg_demand_30d"] = inv["avg_demand_30d"].fillna(inv["avg_daily_sales"])
    inv["demand_std"]     = inv["demand_std"].fillna(inv["avg_daily_sales"] * 0.2)

    # Days of coverage
    inv["days_of_stock"] = inv["current_stock"] / inv["avg_demand_30d"].clip(lower=0.1)

    # Stockout risk (z-score based)
    inv["stockout_risk"] = np.where(
        inv["days_of_stock"] < inv["lead_time_days"],
        np.minimum(1.0, (inv["lead_time_days"] - inv["days_of_stock"]) / inv["lead_time_days"]),
        0.0
    ).round(4)

    # Overstock flag
    inv["overstock_ratio"] = (inv["current_stock"] / (inv["reorder_point"] * 3)).clip(0, 5)
    inv["is_overstock"]    = (inv["overstock_ratio"] > 1.5).astype(int)
    inv["is_understocked"] = (inv["days_of_stock"] < inv["lead_time_days"]).astype(int)

    # Annual holding cost
    inv["annual_holding_cost"] = inv["current_stock"] * inv["unit_cost"] * inv["holding_cost_rate"]

    return inv


def main():
    print("=" * 60)
    print("  Feature Engineering Pipeline")
    print("=" * 60)

    sales, inventory, products, shipments = load_raw()

    demand_feats   = build_demand_features(sales)
    supplier_feats = build_supplier_features(shipments)
    inventory_feats = build_inventory_features(inventory, demand_feats)

    # Save processed datasets
    demand_feats.to_csv(os.path.join(PROCESSED_DIR, "demand_features.csv"), index=False)
    supplier_feats.to_csv(os.path.join(PROCESSED_DIR, "supplier_features.csv"), index=False)
    inventory_feats.to_csv(os.path.join(PROCESSED_DIR, "inventory_features.csv"), index=False)

    print(f"\n  ✅ demand_features.csv    → {len(demand_feats):,} rows")
    print(f"  ✅ supplier_features.csv  → {len(supplier_feats):,} rows")
    print(f"  ✅ inventory_features.csv → {len(inventory_feats):,} rows")
    print(f"\n  Stockout risk: {(inventory_feats['stockout_risk'] > 0.5).sum()} critical products")
    print(f"  Overstocked:   {inventory_feats['is_overstock'].sum()} products")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
