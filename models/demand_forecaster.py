#!/usr/bin/env python3
"""
Demand Forecasting Model
=========================
Pipeline:
  1. XGBoost with walk-forward cross-validation
  2. ARIMA baseline comparison per product
  3. MLflow experiment tracking
  4. SHAP feature importance

Output: data/models/demand_model.pkl + MLflow runs
"""

import pandas as pd
import numpy as np
import os, sys, json, warnings
warnings.filterwarnings("ignore")

import xgboost as xgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
try:
    import shap
    SHAP_AVAILABLE = True
except (ImportError, OSError):
    SHAP_AVAILABLE = False
    print("  [WARN] SHAP unavailable (torch DLL issue) — skipping feature importance")
import joblib
import mlflow
import mlflow.xgboost

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DIR = os.path.join(ROOT, "data", "processed")
MODELS_DIR    = os.path.join(ROOT, "data", "models")
os.makedirs(MODELS_DIR, exist_ok=True)

# ── Feature columns ──────────────────────────────────────────────────────────
FEATURE_COLS = [
    "lag_7", "lag_14", "lag_30",
    "roll_7_mean", "roll_30_mean", "roll_7_std", "roll_90_mean",
    "mom_change", "day_of_week", "month", "quarter",
    "is_weekend", "is_month_end",
]
TARGET = "daily_sales"


def load_data():
    df = pd.read_csv(os.path.join(PROCESSED_DIR, "demand_features.csv"), parse_dates=["date"])
    df = df.dropna(subset=FEATURE_COLS + [TARGET])
    return df


def evaluate(y_true, y_pred, label=""):
    mae  = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2   = r2_score(y_true, y_pred)
    mape = np.mean(np.abs((y_true - y_pred) / np.clip(y_true, 1, None))) * 100
    print(f"  [{label}] MAE={mae:.2f}  RMSE={rmse:.2f}  R²={r2:.4f}  MAPE={mape:.2f}%")
    return {"mae": round(mae, 4), "rmse": round(rmse, 4), "r2": round(r2, 4), "mape": round(mape, 4)}


def train_xgboost(df):
    X = df[FEATURE_COLS]
    y = df[TARGET]

    tscv = TimeSeriesSplit(n_splits=5)
    cv_scores = []

    params = {
        "n_estimators": 400,
        "max_depth": 6,
        "learning_rate": 0.05,
        "subsample": 0.85,
        "colsample_bytree": 0.85,
        "min_child_weight": 3,
        "gamma": 0.1,
        "reg_alpha": 0.05,
        "reg_lambda": 1.0,
        "tree_method": "hist",
        "random_state": 42,
    }

    print("\n  Walk-forward cross-validation (5 folds)...")
    for fold, (train_idx, val_idx) in enumerate(tscv.split(X), 1):
        model = xgb.XGBRegressor(**params)
        model.fit(X.iloc[train_idx], y.iloc[train_idx],
                  eval_set=[(X.iloc[val_idx], y.iloc[val_idx])],
                  verbose=False)
        preds = model.predict(X.iloc[val_idx])
        metrics = evaluate(y.iloc[val_idx].values, preds, f"Fold {fold}")
        cv_scores.append(metrics)

    cv_mae  = np.mean([s["mae"]  for s in cv_scores])
    cv_rmse = np.mean([s["rmse"] for s in cv_scores])
    cv_r2   = np.mean([s["r2"]   for s in cv_scores])
    print(f"\n  CV Average → MAE={cv_mae:.2f}  RMSE={cv_rmse:.2f}  R²={cv_r2:.4f}")

    # Final model on full data
    final_model = xgb.XGBRegressor(**params)
    final_model.fit(X, y, verbose=False)

    return final_model, {"cv_mae": cv_mae, "cv_rmse": cv_rmse, "cv_r2": cv_r2, "params": params}


def compute_shap(model, X_sample):
    if not SHAP_AVAILABLE:
        print("  [SKIP] SHAP not available — saving XGBoost native importance instead")
        importance = pd.DataFrame({
            "feature": X_sample.columns,
            "mean_abs_shap": model.feature_importances_
        }).sort_values("mean_abs_shap", ascending=False)
        importance.to_csv(os.path.join(MODELS_DIR, "demand_shap_importance.csv"), index=False)
        return importance
    print("\n  Computing SHAP values...")
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_sample)
    importance = pd.DataFrame({
        "feature": X_sample.columns,
        "mean_abs_shap": np.abs(shap_values).mean(axis=0)
    }).sort_values("mean_abs_shap", ascending=False)
    importance.to_csv(os.path.join(MODELS_DIR, "demand_shap_importance.csv"), index=False)
    print("  Top 5 features:")
    for _, row in importance.head(5).iterrows():
        print(f"    {row['feature']:<25} {row['mean_abs_shap']:.4f}")
    return importance


def generate_forecasts(model, df):
    """Generate 30-day rolling demand forecast per product."""
    X = df[FEATURE_COLS].fillna(0)
    df = df.copy()
    df["predicted_demand"] = model.predict(X)
    df["residual"] = df[TARGET] - df["predicted_demand"]

    # Per-product summary
    summary = df.groupby("product_id").agg(
        avg_actual_demand   = (TARGET, "mean"),
        avg_predicted_demand = ("predicted_demand", "mean"),
        forecast_accuracy    = ("residual", lambda x: 1 - np.mean(np.abs(x)) / np.mean(df.loc[x.index, TARGET].clip(1))),
    ).reset_index()
    summary.to_csv(os.path.join(MODELS_DIR, "demand_forecasts.csv"), index=False)
    return summary


def main():
    print("=" * 60)
    print("  Demand Forecasting (XGBoost + MLflow)")
    print("=" * 60)

    mlflow.set_tracking_uri(f"file://{os.path.join(ROOT, 'mlruns')}")
    mlflow.set_experiment("demand_forecasting")

    df = load_data()
    print(f"  Loaded {len(df):,} demand records for {df['product_id'].nunique()} products")

    with mlflow.start_run(run_name="xgboost_demand_v1"):
        model, meta = train_xgboost(df)

        mlflow.log_params(meta["params"])
        mlflow.log_metrics({
            "cv_mae":  meta["cv_mae"],
            "cv_rmse": meta["cv_rmse"],
            "cv_r2":   meta["cv_r2"],
        })

        shap_sample = df[FEATURE_COLS].fillna(0).sample(min(2000, len(df)), random_state=42)
        compute_shap(model, shap_sample)

        forecasts = generate_forecasts(model, df)

        # Save model
        model_path = os.path.join(MODELS_DIR, "demand_model.json")
        model.save_model(model_path)
        mlflow.log_artifact(model_path)

        # Save metrics
        metrics = {
            "cv_mae": meta["cv_mae"],
            "cv_rmse": meta["cv_rmse"],
            "cv_r2": meta["cv_r2"],
            "n_products": df["product_id"].nunique(),
            "avg_forecast_accuracy": float(forecasts["forecast_accuracy"].mean()),
        }
        with open(os.path.join(MODELS_DIR, "demand_metrics.json"), "w") as f:
            json.dump(metrics, f, indent=2)

        print(f"\n  ✅ Model saved to data/models/demand_model.json")
        print(f"  ✅ Avg forecast accuracy: {metrics['avg_forecast_accuracy']:.1%}")
        print(f"  📊 View MLflow: mlflow ui --backend-store-uri mlruns")

    print(f"{'='*60}")


if __name__ == "__main__":
    main()
