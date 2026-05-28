"""
Supply Chain Anomaly Detection (PyOD)
Uses the PyOD library to detect anomalies (unusual spikes or drops) in daily sales demand.
"""

import polars as pl
import os
import pickle
import json
import matplotlib.pyplot as plt
from pyod.models.ecod import ECOD
from datetime import datetime

INPUT_FILE = 'dataset/synthetic/sales.csv'
OUTPUT_DIR = 'dataset/processed files'
MODEL_FILE = os.path.join(OUTPUT_DIR, 'anomaly_detector.pkl')
METRICS_FILE = os.path.join(OUTPUT_DIR, 'anomaly_metrics.json')

def load_data(filepath):
    print(f"Loading data from {filepath} with Polars...")
    df = pl.read_csv(filepath)
    
    # We will look for anomalies in daily_sales per product
    # Let's pivot to have products as columns or just use a global model
    # For simplicity and effectiveness, we'll extract statistical features per day
    daily_stats = df.group_by("date").agg([
        pl.col("daily_sales").sum().alias("total_sales"),
        pl.col("daily_sales").mean().alias("avg_sales"),
        pl.col("daily_sales").std().alias("std_sales").fill_null(0.0),
        pl.col("daily_sales").max().alias("max_sales")
    ]).sort("date")
    
    return daily_stats

def main():
    print("=" * 60)
    print("Supply Chain Anomaly Detection (PyOD)")
    print("=" * 60)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df = load_data(INPUT_FILE)
    
    if df.height < 10:
        print("Not enough data to train anomaly detector.")
        return
        
    # Prepare features for PyOD
    feature_cols = ["total_sales", "avg_sales", "std_sales", "max_sales"]
    X = df.select(feature_cols).to_pandas()
    
    print("Training ECOD Anomaly Detector...")
    # ECOD: Empirical Cumulative Distribution Functions for Outlier Detection (fast and parameter-free)
    clf = ECOD()
    clf.fit(X)
    
    # Get anomaly scores and labels
    scores = clf.decision_scores_
    labels = clf.labels_  # 0: inlier, 1: outlier
    
    # Add back to polars dataframe
    df = df.with_columns([
        pl.Series("anomaly_score", scores),
        pl.Series("is_anomaly", labels)
    ])
    
    num_anomalies = df.select(pl.col("is_anomaly").sum()).item()
    print(f"Found {num_anomalies} anomalies out of {df.height} days.")
    
    # Save the model
    with open(MODEL_FILE, 'wb') as f:
        pickle.dump(clf, f)
        
    metrics = {
        "total_records": df.height,
        "anomalies_detected": int(num_anomalies),
        "anomaly_ratio": float(num_anomalies / df.height),
        "trained_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    with open(METRICS_FILE, 'w') as f:
        json.dump(metrics, f, indent=2)
        
    print(f"\nSaved model to {MODEL_FILE}")
    print(f"Saved metrics to {METRICS_FILE}")
    
    # Generate a plot
    pdf = df.to_pandas()
    pdf['date'] = pl.Series(pdf['date']).str.to_datetime("%Y-%m-%d", strict=False)
    
    plt.figure(figsize=(12, 6))
    plt.plot(pdf['date'], pdf['total_sales'], label='Total Sales', color='blue', alpha=0.6)
    
    # Highlight anomalies
    anomalies = pdf[pdf['is_anomaly'] == 1]
    plt.scatter(anomalies['date'], anomalies['total_sales'], color='red', label='Anomaly', zorder=5)
    
    plt.title("Supply Chain Demand Anomalies")
    plt.xlabel("Date")
    plt.ylabel("Total Sales")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'anomaly_detection.png'))
    plt.close()
    
    print("=" * 60)

if __name__ == "__main__":
    main()
