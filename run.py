#!/usr/bin/env python3
"""
AI Supply Chain Control Tower -- One-Command Runner
===================================================
Usage:
    python run.py                  # Run full pipeline (default: all)
    python run.py --mode generate  # Generate synthetic data only
    python run.py --mode features  # Feature engineering only
    python run.py --mode train     # Train all models
    python run.py --mode dashboard # Launch Streamlit dashboard
    python run.py --mode all       # Full end-to-end pipeline
"""

import sys
# Force UTF-8 output so emoji/special chars work on Windows cp1252 terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import argparse
import subprocess
import sys
import os
import time

PYTHON = sys.executable
ROOT = os.path.dirname(os.path.abspath(__file__))


def run(cmd, label):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    result = subprocess.run([PYTHON] + cmd, cwd=ROOT)
    if result.returncode != 0:
        print(f"  [FAILED] {label}")
        sys.exit(1)
    print(f"  [OK] {label}")


def main():
    parser = argparse.ArgumentParser(description="AI Supply Chain Control Tower")
    parser.add_argument(
        "--mode",
        choices=["generate", "features", "train", "dashboard", "all"],
        default="all",
        help="Pipeline stage to run"
    )
    args = parser.parse_args()

    start = time.time()

    if args.mode in ("generate", "all"):
        run(["data_simulator/generate.py"], "1/4 Generating Synthetic Supply Chain Data")

    if args.mode in ("features", "all"):
        run(["feature_engineering/pipeline.py"], "2/4 Feature Engineering Pipeline")

    if args.mode in ("train", "all"):
        run(["models/demand_forecaster.py"],    "3a/4 XGBoost Demand Forecasting + ARIMA + MLflow")
        run(["models/anomaly_detector.py"],     "3b/4 Ensemble Anomaly Detection (ECOD + IForest + LOF)")
        run(["models/supplier_risk.py"],        "3c/4 Supplier Risk Model (Optuna + XGBoost + SHAP)")
        run(["models/inventory_optimizer.py"],  "3d/4 Inventory Optimization (EOQ + Safety Stock)")
        # Time-series is supplementary — soft failure allowed
        print(f"\n{'='*60}")
        print(f"  3e/4 Time-Series Forecasting (SARIMAX / Holt ES)")
        print(f"{'='*60}")
        result = subprocess.run([PYTHON, "models/time_series.py"], cwd=ROOT)
        if result.returncode != 0:
            print("  [WARN] Time-series step failed (optional) — skipping")
        else:
            print("  [OK] 3e/4 Time-Series Forecasting")

    if args.mode in ("dashboard", "all"):
        elapsed = time.time() - start
        print(f"\n{'='*60}")
        print(f"  Pipeline complete in {elapsed:.1f}s")
        print(f"  Launching dashboard at http://localhost:8501")
        print(f"{'='*60}\n")
        subprocess.run([
            PYTHON, "-m", "streamlit", "run", "dashboard/app.py",
            "--server.headless=true",
            "--browser.gatherUsageStats=false"
        ])


if __name__ == "__main__":
    main()
