#!/usr/bin/env python3
"""
Supplier Risk Model
=====================
XGBoost + Optuna hyperparameter tuning + full SHAP analysis.
Predicts: supplier reliability score (0-100) and risk tier (LOW/MEDIUM/HIGH)

Output: data/models/supplier_risk_model.json + shap plots
"""

import pandas as pd
import numpy as np
import os, json, warnings
warnings.filterwarnings("ignore")

import xgboost as xgb
import optuna
optuna.logging.set_verbosity(optuna.logging.WARNING)
import shap
from sklearn.model_selection import cross_val_score, KFold
from sklearn.metrics import mean_absolute_error, r2_score
import joblib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DIR = os.path.join(ROOT, "data", "processed")
MODELS_DIR    = os.path.join(ROOT, "data", "models")
os.makedirs(MODELS_DIR, exist_ok=True)

FEATURE_COLS = [
    "total_shipments", "avg_delay_days", "max_delay_days",
    "on_time_rate", "avg_defect_units", "avg_order_value",
    "recent_90d_on_time_rate",
]
TARGET = "supplier_risk_score"


def load_data():
    df = pd.read_csv(os.path.join(PROCESSED_DIR, "supplier_features.csv"))
    df = df.dropna(subset=FEATURE_COLS + [TARGET])
    return df


def optuna_objective(trial, X, y):
    params = {
        "n_estimators":     trial.suggest_int("n_estimators", 100, 600),
        "max_depth":        trial.suggest_int("max_depth", 3, 8),
        "learning_rate":    trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        "subsample":        trial.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
        "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
        "gamma":            trial.suggest_float("gamma", 0.0, 0.5),
        "reg_alpha":        trial.suggest_float("reg_alpha", 0.0, 1.0),
        "reg_lambda":       trial.suggest_float("reg_lambda", 0.5, 2.0),
        "tree_method": "hist",
        "random_state":  42,
    }
    model = xgb.XGBRegressor(**params)
    scores = cross_val_score(model, X, y, cv=KFold(5, shuffle=True, random_state=42),
                             scoring="neg_root_mean_squared_error")
    return -scores.mean()


def main():
    print("=" * 60)
    print("  Supplier Risk Model (Optuna + XGBoost + SHAP)")
    print("=" * 60)

    df = load_data()
    print(f"  Loaded {len(df)} suppliers")

    X = df[FEATURE_COLS]
    y = df[TARGET]

    # ── Optuna Hyperparameter Search ─────────────────────────────────────────
    print("\n  Optuna hyperparameter tuning (50 trials)...")
    study = optuna.create_study(direction="minimize", study_name="supplier_risk")
    study.optimize(lambda t: optuna_objective(t, X, y), n_trials=50, show_progress_bar=False)

    best_params = study.best_params
    best_params["tree_method"] = "hist"
    best_params["random_state"] = 42
    print(f"  Best RMSE: {study.best_value:.4f}")
    print(f"  Best params: n_estimators={best_params['n_estimators']}, "
          f"max_depth={best_params['max_depth']}, "
          f"lr={best_params['learning_rate']:.4f}")

    # ── Final Model ───────────────────────────────────────────────────────────
    model = xgb.XGBRegressor(**best_params)
    model.fit(X, y)

    preds = model.predict(X)
    mae = mean_absolute_error(y, preds)
    r2  = r2_score(y, preds)
    print(f"\n  Final Model → MAE={mae:.4f}  R²={r2:.4f}")

    # Risk tier predictions
    df["predicted_risk_score"] = preds
    df["predicted_risk_tier"] = pd.cut(
        df["predicted_risk_score"],
        bins=[0, 0.2, 0.4, 1.0],
        labels=["LOW", "MEDIUM", "HIGH"]
    )

    # ── SHAP Analysis ─────────────────────────────────────────────────────────
    print("\n  Computing SHAP values...")
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)

    shap_importance = pd.DataFrame({
        "feature": X.columns,
        "mean_abs_shap": np.abs(shap_values).mean(axis=0)
    }).sort_values("mean_abs_shap", ascending=False)

    shap_importance.to_csv(os.path.join(MODELS_DIR, "supplier_shap_importance.csv"), index=False)

    print("  Top features driving supplier risk:")
    for _, row in shap_importance.iterrows():
        bar = "█" * int(row["mean_abs_shap"] * 100 / shap_importance["mean_abs_shap"].max() * 20)
        print(f"    {row['feature']:<30} {bar:<20} {row['mean_abs_shap']:.4f}")

    # Per-supplier SHAP breakdown
    shap_df = pd.DataFrame(shap_values, columns=X.columns)
    shap_df.insert(0, "supplier_id", df["supplier_id"].values)
    shap_df.to_csv(os.path.join(MODELS_DIR, "supplier_shap_values.csv"), index=False)

    # ── Save Results ──────────────────────────────────────────────────────────
    results = df[["supplier_id", "on_time_rate", "avg_delay_days",
                  "avg_defect_units", "supplier_risk_score",
                  "predicted_risk_score", "predicted_risk_tier"]].copy()
    results.to_csv(os.path.join(MODELS_DIR, "supplier_risk_results.csv"), index=False)

    model.save_model(os.path.join(MODELS_DIR, "supplier_risk_model.json"))

    metrics = {
        "n_suppliers": len(df),
        "mae": round(mae, 4),
        "r2": round(r2, 4),
        "best_rmse_cv": round(study.best_value, 4),
        "n_optuna_trials": 50,
        "high_risk_suppliers": int((df["predicted_risk_tier"] == "HIGH").sum()),
        "medium_risk_suppliers": int((df["predicted_risk_tier"] == "MEDIUM").sum()),
        "low_risk_suppliers": int((df["predicted_risk_tier"] == "LOW").sum()),
    }
    with open(os.path.join(MODELS_DIR, "supplier_risk_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"\n  ✅ High risk: {metrics['high_risk_suppliers']} suppliers")
    print(f"  ✅ Model saved to data/models/supplier_risk_model.json")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
