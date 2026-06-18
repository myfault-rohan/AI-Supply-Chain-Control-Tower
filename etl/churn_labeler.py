"""
etl/churn_labeler.py
====================
Generates the observation dataset (features + labels) for model training.
Defines the churn label and ensures temporal separation.
"""

import os
import pandas as pd
import numpy as np
from etl.seller_feature_builder import build_features_for_date

# ── Path configuration ──────────────────────────────────────────────────────
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROCESSED_DIR = os.path.join(ROOT, "data", "processed")

def get_churn_labels(master: pd.DataFrame, observation_date: pd.Timestamp) -> pd.DataFrame:
    """
    Returns a dataframe of active sellers at observation_date with their churn label.
    
    Active definition: >= 3 orders in [T - 60 days, T]
    Churn definition: 0 orders in [T + 1 day, T + 45 days]
    """
    t_minus_60 = observation_date - pd.Timedelta(days=60)
    t_plus_1 = observation_date + pd.Timedelta(days=1)
    t_plus_45 = observation_date + pd.Timedelta(days=45)
    
    # 1. Find active sellers (>=3 orders in 60 days prior to T)
    active_mask = (master["order_purchase_timestamp"] >= t_minus_60) & (master["order_purchase_timestamp"] <= observation_date)
    orders_60d = master[active_mask].groupby("seller_id").size()
    active_sellers = orders_60d[orders_60d >= 3].index
    
    # 2. Find sellers who had orders in the 45 days AFTER T
    future_mask = (master["order_purchase_timestamp"] >= t_plus_1) & (master["order_purchase_timestamp"] <= t_plus_45)
    surviving_sellers = master[future_mask]["seller_id"].unique()
    
    # 3. Churn label (1 if active but not surviving, 0 otherwise)
    labels = pd.DataFrame({"seller_id": active_sellers})
    labels["churned"] = (~labels["seller_id"].isin(surviving_sellers)).astype(int)
    
    return labels

def create_training_dataset(master: pd.DataFrame, obs_dates: list) -> pd.DataFrame:
    """
    Given a list of observation dates, builds features and labels for each,
    and concatenates them into a single training dataset.
    """
    all_data = []
    
    for date_str in obs_dates:
        obs_date = pd.Timestamp(date_str)
        print(f"Processing observation date: {obs_date.date()}...")
        
        # Get labels first (filters to active sellers only)
        labels = get_churn_labels(master, obs_date)
        if len(labels) == 0:
            print(f"  No active sellers found for {obs_date.date()}. Skipping.")
            continue
            
        # Get features
        features = build_features_for_date(master, obs_date)
        
        # Merge
        dataset = labels.merge(features, on="seller_id", how="inner")
        dataset["observation_date"] = obs_date
        
        all_data.append(dataset)
        
    final_df = pd.concat(all_data, ignore_index=True)
    return final_df

if __name__ == "__main__":
    print("=" * 65)
    print("  Churn Labeler & Dataset Builder")
    print("=" * 65)
    master_path = os.path.join(PROCESSED_DIR, "master.parquet")
    if not os.path.exists(master_path):
        print("Run olist_loader.py first to generate master.parquet")
        exit(1)
        
    master = pd.read_parquet(master_path)
    
    # Define observation dates based on the plan
    # Train: 2017-01 to 2017-10
    # Test: 2018-01 to 2018-06
    # We will sample the end of each month
    
    train_dates = pd.date_range(start="2017-01-31", end="2017-10-31", freq="M").strftime("%Y-%m-%d").tolist()
    test_dates = pd.date_range(start="2018-01-31", end="2018-06-30", freq="M").strftime("%Y-%m-%d").tolist()
    
    print("\n--- Building Training Set ---")
    train_df = create_training_dataset(master, train_dates)
    
    print("\n--- Building Test Set ---")
    test_df = create_training_dataset(master, test_dates)
    
    # Save the datasets
    train_df.to_parquet(os.path.join(PROCESSED_DIR, "train_dataset.parquet"), index=False)
    test_df.to_parquet(os.path.join(PROCESSED_DIR, "test_dataset.parquet"), index=False)
    
    # Validation checks
    print("\n" + "=" * 65)
    print("  DATASET VALIDATION SUMMARY")
    print("=" * 65)
    
    for name, df in [("Train", train_df), ("Test", test_df)]:
        total = len(df)
        churned = df["churned"].sum()
        churn_rate = churned / total * 100
        
        print(f"{name} Set: {total:,} rows")
        print(f"  Churned:    {churned:,} ({churn_rate:.1f}%)")
        print(f"  Surviving:  {total - churned:,} ({(100 - churn_rate):.1f}%)")
        print()
        
    print("=" * 65)
