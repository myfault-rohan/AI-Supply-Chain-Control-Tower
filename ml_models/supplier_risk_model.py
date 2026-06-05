"""
Supplier Risk Model (Optuna + XGBoost)
Uses Optuna to find the best hyperparameter configuration for an XGBoost model
that predicts shipment delays.
"""

import polars as pl
import xgboost as xgb
import optuna
import sys
try:
    import torch
except OSError:
    sys.modules['torch'] = None
import shap
import json
import os
import pickle
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score

INPUT_FILE = 'dataset/synthetic/shipments.csv'
OUTPUT_DIR = 'dataset/processed files'
MODEL_FILE = os.path.join(OUTPUT_DIR, 'supplier_risk_model.pkl')
METRICS_FILE = os.path.join(OUTPUT_DIR, 'supplier_risk_metrics.json')

def load_data(filepath):
    print(f"Loading data from {filepath} with Polars...")
    df = pl.read_csv(filepath)
    
    # Calculate delay in days
    df = df.with_columns([
        pl.col("expected_delivery").str.to_datetime("%Y-%m-%d", strict=False).cast(pl.Date),
        pl.col("actual_delivery").str.to_datetime("%Y-%m-%d", strict=False).cast(pl.Date)
    ])
    
    # Target: Delay days (actual - expected)
    df = df.with_columns(
        (pl.col("actual_delivery") - pl.col("expected_delivery")).dt.days().alias("delay_days")
    )
    
    # Drop rows with null delay_days (e.g. pending shipments)
    df = df.filter(pl.col("delay_days").is_not_null())
    
    return df

def engineer_features(df):
    """Simple feature engineering for supplier risk"""
    print("Engineering features...")
    
    # Calculate supplier reliability profile
    supplier_profile = df.group_by("supplier_id").agg([
        pl.col("delay_days").mean().alias("avg_supplier_delay"),
        pl.col("delay_days").std().alias("std_supplier_delay").fill_null(0.0),
        (pl.col("delay_days") > 0).mean().alias("supplier_late_ratio")
    ])
    
    df = df.join(supplier_profile, on="supplier_id", how="left")
    
    # We will use label encoding for supplier_id and product_id
    from sklearn.preprocessing import LabelEncoder
    le_sup = LabelEncoder()
    le_prod = LabelEncoder()
    
    supplier_encoded = le_sup.fit_transform(df["supplier_id"].to_numpy().astype(str))
    product_encoded = le_prod.fit_transform(df["product_id"].to_numpy().astype(str))
    
    df = df.with_columns([
        pl.Series("supplier_encoded", supplier_encoded),
        pl.Series("product_encoded", product_encoded)
    ])
    
    features = ["supplier_encoded", "product_encoded", "avg_supplier_delay", "std_supplier_delay", "supplier_late_ratio"]
    target = "delay_days"
    
    return df.select(features).to_pandas(), df.select(target).to_pandas()[target], le_sup, le_prod

def objective(trial, X_train, y_train, X_valid, y_valid):
    """Optuna objective function for XGBoost"""
    param = {
        "verbosity": 0,
        "objective": "reg:squarederror",
        "n_estimators": trial.suggest_int("n_estimators", 50, 300),
        "max_depth": trial.suggest_int("max_depth", 3, 9),
        "learning_rate": trial.suggest_float("learning_rate", 1e-3, 0.1, log=True),
        "subsample": trial.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
        "random_state": 42
    }
    
    model = xgb.XGBRegressor(**param)
    model.fit(X_train, y_train, eval_set=[(X_valid, y_valid)], verbose=False)
    
    preds = model.predict(X_valid)
    rmse = mean_squared_error(y_valid, preds) ** 0.5
    return rmse

def main():
    print("=" * 60)
    print("Supplier Risk ML Pipeline (Optuna + XGBoost)")
    print("=" * 60)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    df = load_data(INPUT_FILE)
    X, y, le_sup, le_prod = engineer_features(df)
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    X_train_opt, X_valid, y_train_opt, y_valid = train_test_split(X_train, y_train, test_size=0.2, random_state=42)
    
    print("Starting Optuna hyperparameter tuning...")
    study = optuna.create_study(direction="minimize")
    
    # Run Optuna for 20 trials for demonstration
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study.optimize(lambda trial: objective(trial, X_train_opt, y_train_opt, X_valid, y_valid), n_trials=20)
    
    print(f"\nBest hyperparameters found by Optuna:")
    for key, value in study.best_params.items():
        print(f"  {key}: {value}")
        
    print("\nTraining final model with best hyperparameters...")
    best_params = study.best_params
    best_params["random_state"] = 42
    best_params["objective"] = "reg:squarederror"
    
    model = xgb.XGBRegressor(**best_params)
    model.fit(X_train, y_train)
    
    preds = model.predict(X_test)
    rmse = mean_squared_error(y_test, preds) ** 0.5
    r2 = r2_score(y_test, preds)
    
    print(f"Final Model Performance on Test Set:")
    print(f"  RMSE: {rmse:.4f}")
    print(f"  R2:   {r2:.4f}")
    
    # SHAP
    print("\nGenerating SHAP explainability...")
    explainer = shap.Explainer(model, X_train)
    shap_values = explainer(X_test)
    
    plt.figure(figsize=(10, 8))
    shap.summary_plot(shap_values, X_test, show=False)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'shap_supplier_risk.png'))
    plt.close()
    
    # Save model — use XGBoost JSON format to avoid binary deprecation warning
    model.save_model(os.path.join(OUTPUT_DIR, 'supplier_risk_model.json'))
    # Also save full pipeline (label encoders + feature list) as pickle
    with open(MODEL_FILE, 'wb') as f:
        pickle.dump({
            'features': list(X.columns),
            'le_sup': le_sup,
            'le_prod': le_prod,
            'model_path': os.path.join(OUTPUT_DIR, 'supplier_risk_model.json')
        }, f)

    with open(METRICS_FILE, 'w') as f:
        json.dump({
            "rmse": rmse,
            "r2": r2,
            "best_params": study.best_params
        }, f, indent=2)

    print(f"\nSaved model to {MODEL_FILE}")
    print(f"Saved metrics to {METRICS_FILE}")
    print("=" * 60)
    
if __name__ == "__main__":
    main()
