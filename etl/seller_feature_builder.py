"""
etl/seller_feature_builder.py
=============================
Computes rolling behavioral features for sellers at a specific observation date (T).

Features are computed using data strictly from the window [T - 8 weeks, T] to prevent leakage.
"""

import os
import pandas as pd
import numpy as np

# ── Path configuration ──────────────────────────────────────────────────────
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROCESSED_DIR = os.path.join(ROOT, "data", "processed")

def _safe_slope(y):
    """Calculate OLS slope for an array y. Return 0 if insufficient data."""
    if len(y) < 2:
        return 0.0
    # x is just the sequence index 0, 1, 2...
    x = np.arange(len(y))
    # Add small noise to avoid RankWarning if all y are identical
    if np.all(y == y[0]):
        return 0.0
    return np.polyfit(x, y, deg=1)[0]

def build_features_for_date(master: pd.DataFrame, observation_date: pd.Timestamp) -> pd.DataFrame:
    """
    Builds feature matrix for all sellers active before `observation_date`.
    Only considers orders placed BEFORE `observation_date`.
    """
    # 1. Filter out all orders placed after the observation date (LEAKAGE PREVENTION)
    df = master[master["order_purchase_timestamp"] < observation_date].copy()
    
    # 2. Time windows
    t_minus_30 = observation_date - pd.Timedelta(days=30)
    t_minus_56 = observation_date - pd.Timedelta(days=56) # 8 weeks
    t_minus_7  = observation_date - pd.Timedelta(days=7)
    
    # Masks
    mask_8w = df["order_purchase_timestamp"] >= t_minus_56
    mask_30d = df["order_purchase_timestamp"] >= t_minus_30
    mask_7d = df["order_purchase_timestamp"] >= t_minus_7
    
    # Base dataframe for features (one row per seller seen in the past 8 weeks)
    active_sellers_8w = df[mask_8w]["seller_id"].unique()
    features = pd.DataFrame({"seller_id": active_sellers_8w})
    
    # ── Seller State ────────────────────────────────────────────────────────
    # (static, just take the first we see)
    state_map = df.drop_duplicates("seller_id").set_index("seller_id")["seller_state"]
    features["seller_state"] = features["seller_id"].map(state_map)
    
    # ── Tenure ──────────────────────────────────────────────────────────────
    first_order_map = df.groupby("seller_id")["order_purchase_timestamp"].min()
    features["seller_tenure_days"] = (observation_date - features["seller_id"].map(first_order_map)).dt.days
    
    # =========================================================================
    # 30-Day Window Features
    # =========================================================================
    df_30d = df[mask_30d]
    
    # Order volume in 30d
    vol_30d = df_30d.groupby("seller_id").size()
    features["orders_30d"] = features["seller_id"].map(vol_30d).fillna(0)
    
    # OTD Rate
    # Only count delivered orders when calculating OTD
    delivered_30d = df_30d[df_30d["order_status"] == "delivered"]
    otd_count = delivered_30d[delivered_30d["on_time"] == True].groupby("seller_id").size()
    total_delivered = delivered_30d.groupby("seller_id").size()
    otd_rate = (otd_count / total_delivered).fillna(1.0) # default to 1.0 if no delivered orders
    features["rolling_30d_otd_rate"] = features["seller_id"].map(otd_rate).fillna(1.0)
    
    # Reviews (Avg, Complaint Rate, Revenue at Risk)
    rev_mean = df_30d.groupby("seller_id")["review_score"].mean()
    features["rolling_30d_avg_review"] = features["seller_id"].map(rev_mean).fillna(5.0) # Assume 5.0 if missing
    
    complaints = df_30d[df_30d["review_score"] <= 2.0]
    complaint_count = complaints.groupby("seller_id").size()
    features["high_complaint_rate_30d"] = (features["seller_id"].map(complaint_count).fillna(0) / features["orders_30d"].replace(0, 1)).fillna(0)
    
    revenue_at_risk = complaints.groupby("seller_id")["price"].sum()
    features["revenue_at_risk_30d"] = features["seller_id"].map(revenue_at_risk).fillna(0.0)
    
    # Cancellation rate
    cancelled_30d = df_30d[df_30d["order_status"] == "canceled"].groupby("seller_id").size()
    features["cancellation_rate_30d"] = (features["seller_id"].map(cancelled_30d).fillna(0) / features["orders_30d"].replace(0, 1)).fillna(0)
    
    # Category diversity
    cat_diversity = df_30d.groupby("seller_id")["product_category_name"].nunique()
    features["product_category_diversity"] = features["seller_id"].map(cat_diversity).fillna(0)
    
    # =========================================================================
    # 7-Day Window Features
    # =========================================================================
    df_7d = df[mask_7d]
    dispatch_7d = df_7d[df_7d["dispatch_days"] > 0].groupby("seller_id")["dispatch_days"].median()
    features["dispatch_time_p50_7d"] = features["seller_id"].map(dispatch_7d).fillna(0.0)
    
    # =========================================================================
    # 8-Week Trend Features (Slopes)
    # =========================================================================
    df_8w = df[mask_8w].copy()
    
    # Create week index (0 to 7)
    df_8w["week_idx"] = ((df_8w["order_purchase_timestamp"] - t_minus_56).dt.days // 7).clip(0, 7)
    
    # Active weeks
    active_weeks = df_8w.groupby("seller_id")["week_idx"].nunique()
    features["seller_active_weeks"] = features["seller_id"].map(active_weeks).fillna(0)
    
    # We need to aggregate by seller AND week to compute slopes
    # To ensure 0 values for weeks with no activity, we unstack
    
    # 1. Volume Slope
    vol_weekly = df_8w.groupby(["seller_id", "week_idx"]).size().unstack(fill_value=0)
    features["order_volume_slope"] = features["seller_id"].map(
        lambda sid: _safe_slope(vol_weekly.loc[sid].values) if sid in vol_weekly.index else 0.0
    )
    
    # 2. Dispatch Delay Slope
    disp_weekly = df_8w[df_8w["dispatch_days"] > 0].groupby(["seller_id", "week_idx"])["dispatch_days"].median().unstack()
    # Forward fill then backward fill missing weeks for dispatch time
    disp_weekly = disp_weekly.ffill(axis=1).bfill(axis=1).fillna(0) 
    features["dispatch_delay_slope"] = features["seller_id"].map(
        lambda sid: _safe_slope(disp_weekly.loc[sid].values) if sid in disp_weekly.index else 0.0
    )
    
    # 3. Review Score Slope
    rev_weekly = df_8w.groupby(["seller_id", "week_idx"])["review_score"].mean().unstack()
    rev_weekly = rev_weekly.ffill(axis=1).bfill(axis=1).fillna(5.0)
    features["review_score_slope"] = features["seller_id"].map(
        lambda sid: _safe_slope(rev_weekly.loc[sid].values) if sid in rev_weekly.index else 0.0
    )
    
    return features


if __name__ == "__main__":
    print("=" * 65)
    print("  Feature Builder — Validation Run")
    print("=" * 65)
    master_path = os.path.join(PROCESSED_DIR, "master.parquet")
    if not os.path.exists(master_path):
        print("Run olist_loader.py first to generate master.parquet")
        exit(1)
        
    master = pd.read_parquet(master_path)
    
    # Pick a random date in the middle of the dataset for validation
    test_date = pd.Timestamp("2018-05-01")
    print(f"Building features for observation date: {test_date.date()}")
    
    features = build_features_for_date(master, test_date)
    
    print(f"\nExtracted features for {len(features):,} active sellers.")
    
    # Show 3 random sellers
    sample = features.sample(3, random_state=42)
    print("\nSample Sellers:")
    print(sample.T)
    print("=" * 65)
