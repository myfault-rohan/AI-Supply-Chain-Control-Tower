#!/usr/bin/env python3
"""
Ensemble Anomaly Detection
===========================
Three algorithms + majority vote ensemble:
  - ECOD  (Empirical Cumulative Distribution)
  - Isolation Forest
  - Local Outlier Factor (LOF)

Ensemble reduces false positive rate significantly vs any single model.

Output: data/models/anomaly_*.pkl + anomaly_results.csv
"""

import pandas as pd
import numpy as np
import os, json, warnings
warnings.filterwarnings("ignore")

from pyod.models.ecod import ECOD
from pyod.models.iforest import IForest
from pyod.models.lof import LOF
from sklearn.preprocessing import StandardScaler
import joblib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DIR = os.path.join(ROOT, "data", "processed")
MODELS_DIR    = os.path.join(ROOT, "data", "models")
os.makedirs(MODELS_DIR, exist_ok=True)

# Contamination rate (expected % of anomalies)
CONTAMINATION = 0.07

FEATURE_COLS = [
    "roll_7_mean", "roll_30_mean", "roll_7_std", "lag_7", "lag_30",
    "mom_change", "day_of_week", "month", "is_weekend",
]


def load_data():
    df = pd.read_csv(os.path.join(PROCESSED_DIR, "demand_features.csv"), parse_dates=["date"])
    df = df.dropna(subset=FEATURE_COLS).replace([np.inf, -np.inf], np.nan).dropna(subset=FEATURE_COLS)
    return df


def train_detectors(X_scaled):
    """Train all 3 detectors."""
    detectors = {
        "ECOD":       ECOD(contamination=CONTAMINATION),
        "IForest":    IForest(contamination=CONTAMINATION, n_estimators=200, random_state=42),
        "LOF":        LOF(contamination=CONTAMINATION, n_neighbors=20),
    }
    scores = {}
    preds  = {}
    for name, det in detectors.items():
        print(f"  Training {name}...")
        det.fit(X_scaled)
        scores[name] = det.decision_scores_
        preds[name]  = det.labels_  # 0=normal, 1=anomaly
        joblib.dump(det, os.path.join(MODELS_DIR, f"anomaly_{name.lower()}.pkl"))

    return detectors, scores, preds


def ensemble_vote(preds):
    """Majority vote: anomaly if ≥ 2/3 detectors agree."""
    votes = np.column_stack(list(preds.values()))
    return (votes.sum(axis=1) >= 2).astype(int)


def compute_anomaly_scores(scores):
    """Normalize and average scores across detectors."""
    normalized = {}
    for name, s in scores.items():
        s_min, s_max = s.min(), s.max()
        normalized[name] = (s - s_min) / (s_max - s_min + 1e-8)
    stacked = np.column_stack(list(normalized.values()))
    return stacked.mean(axis=1)


def main():
    print("=" * 60)
    print("  Ensemble Anomaly Detection (ECOD + IForest + LOF)")
    print("=" * 60)

    df = load_data()
    print(f"  Loaded {len(df):,} records")

    X = df[FEATURE_COLS].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    joblib.dump(scaler, os.path.join(MODELS_DIR, "anomaly_scaler.pkl"))

    detectors, scores, preds = train_detectors(X_scaled)

    # Ensemble
    ensemble_labels = ensemble_vote(preds)
    ensemble_scores = compute_anomaly_scores(scores)

    df["anomaly_label"]   = ensemble_labels
    df["anomaly_score"]   = ensemble_scores.round(4)
    df["ecod_flag"]       = preds["ECOD"]
    df["iforest_flag"]    = preds["IForest"]
    df["lof_flag"]        = preds["LOF"]

    n_anomalies = ensemble_labels.sum()
    rate = n_anomalies / len(df) * 100

    print(f"\n  Results:")
    print(f"    ECOD anomalies:    {preds['ECOD'].sum():,}")
    print(f"    IForest anomalies: {preds['IForest'].sum():,}")
    print(f"    LOF anomalies:     {preds['LOF'].sum():,}")
    print(f"    Ensemble (≥2/3):   {n_anomalies:,} ({rate:.1f}%)")

    # Per-product anomaly summary
    product_summary = df.groupby("product_id").agg(
        total_records   = ("anomaly_label", "count"),
        anomaly_count   = ("anomaly_label", "sum"),
        avg_anomaly_score = ("anomaly_score", "mean"),
        max_anomaly_score = ("anomaly_score", "max"),
    ).reset_index()
    product_summary["anomaly_rate"] = (product_summary["anomaly_count"] / product_summary["total_records"]).round(4)
    product_summary["risk_flag"] = (product_summary["anomaly_rate"] > 0.10).astype(int)

    # Save results
    results = df[["date", "product_id", "category", "daily_sales",
                  "anomaly_label", "anomaly_score", "ecod_flag", "iforest_flag", "lof_flag"]]
    results.to_csv(os.path.join(MODELS_DIR, "anomaly_results.csv"), index=False)
    product_summary.to_csv(os.path.join(MODELS_DIR, "anomaly_product_summary.csv"), index=False)

    metrics = {
        "total_records": int(len(df)),
        "total_anomalies": int(n_anomalies),
        "anomaly_rate": round(rate, 4),
        "high_risk_products": int(product_summary["risk_flag"].sum()),
        "algorithms": ["ECOD", "IForest", "LOF"],
        "ensemble_strategy": "majority_vote_2_of_3",
    }
    with open(os.path.join(MODELS_DIR, "anomaly_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"\n  ✅ Anomaly results saved")
    print(f"  ✅ High-risk products: {product_summary['risk_flag'].sum()}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
