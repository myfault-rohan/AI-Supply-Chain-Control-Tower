"""
Supply Chain Demand Forecasting Pipeline
Trains an XGBoost model to predict daily sales and calculates stockout risk.
Outputs to dataset/processed files/ for consistency with the API layer.

Model Card:
  Model: XGBoost Demand Forecaster v2
  Data Engine: Polars (Replaced Pandas for extreme speed)
  Features: 12 engineered features (inventory, sales, timing, supplier metrics)
  Target: avg_daily_sales
  Last trained: auto-recorded on each run
  Performance: MAE, RMSE, R², MAPE logged to console
"""

import polars as pl
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import os
import json
import pickle
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import sys
try:
    import torch
except OSError:
    sys.modules['torch'] = None
import shap
import matplotlib.pyplot as plt

# Configuration
INPUT_FILE = 'dataset/processed_supply_chain.csv'
OUTPUT_DIR = 'dataset/processed files'
OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'demand_predictions.csv')
MODEL_FILE = os.path.join(OUTPUT_DIR, 'demand_model.pkl')
METRICS_FILE = os.path.join(OUTPUT_DIR, 'model_metrics.json')

def load_data(filepath):
    """Load the processed supply chain dataset using Polars"""
    print(f"Loading data from {filepath} with Polars...")
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Dataset not found at {filepath}")
    
    df = pl.read_csv(filepath)
    print(f"Loaded {df.height} records with columns: {df.columns}")
    return df

def engineer_features(df):
    """Create 12+ engineered features using Blazing Fast Polars Expressions"""
    print("Engineering features using Polars...")
    
    import pandas as pd
    is_pandas = isinstance(df, pd.DataFrame)
    if is_pandas:
        df = pl.from_pandas(df)
        
    cols = df.columns
    
    # Ensure required base columns exist with defaults
    if 'avg_daily_sales' not in cols:
        df = df.with_columns(pl.col('daily_demand').alias('avg_daily_sales').fill_null(1.0))
    if 'avg_delay_days' not in cols:
        df = df.with_columns(pl.lit(0).alias('avg_delay_days'))
    if 'inventory_days' not in cols and 'current_stock' in cols:
        df = df.with_columns(
            pl.when(pl.col('avg_daily_sales') > 0)
            .then(pl.col('current_stock') / pl.col('avg_daily_sales'))
            .otherwise(9999).alias('inventory_days')
        )
    
    exprs = []
    
    # Feature 2 & 10 & 12: safety stock interactions
    if 'safety_stock' in cols:
        exprs.append(
            pl.when(pl.col('safety_stock') > 0)
            .then(pl.col('current_stock') / pl.col('safety_stock'))
            .otherwise(pl.col('current_stock')).alias('stock_to_safety_ratio')
        )
        exprs.append((pl.col('current_stock') - pl.col('safety_stock')).alias('excess_stock'))
        exprs.append((pl.col('safety_stock') / (pl.col('current_stock') + 1)).alias('inventory_pressure'))
    else:
        exprs.append(pl.lit(1.0).alias('stock_to_safety_ratio'))
        exprs.append(pl.col('current_stock').alias('excess_stock'))
        exprs.append(pl.lit(0.0).alias('inventory_pressure'))
    
    # Feature 3 & 5: reorder point interactions
    if 'reorder_point' in cols:
        exprs.append(
            pl.when(pl.col('reorder_point') > 0)
            .then(pl.col('current_stock') / pl.col('reorder_point'))
            .otherwise(pl.col('current_stock')).alias('stock_to_reorder_ratio')
        )
        exprs.append((pl.col('current_stock') > pl.col('reorder_point')).cast(pl.Int32).alias('is_high_stock'))
    else:
        exprs.append(pl.lit(1.0).alias('stock_to_reorder_ratio'))
        exprs.append(pl.lit(1).alias('is_high_stock'))
    
    # Feature 4: demand_volatility (stddev / mean of daily sales)
    if 'stddev_daily_sales' in cols:
        exprs.append(
            pl.when(pl.col('avg_daily_sales') > 0)
            .then(pl.col('stddev_daily_sales') / pl.col('avg_daily_sales'))
            .otherwise(0.0).alias('demand_volatility')
        )
    else:
        exprs.append(pl.lit(0.0).alias('demand_volatility'))
    
    # Feature 6: delay_risk
    exprs.append((pl.col('avg_delay_days') > 2).cast(pl.Int32).alias('delay_risk'))
    
    # Feature 7 & 8: counts
    if 'total_delays' not in cols:
        exprs.append(pl.lit(0).alias('total_delays'))
    if 'total_spikes' not in cols:
        exprs.append(pl.lit(0).alias('total_spikes'))
    
    # Feature 9: demand_spike_int
    if 'demand_spike' not in cols:
        exprs.append(pl.lit(0).alias('demand_spike_int'))
    else:
        exprs.append(pl.col('demand_spike').cast(pl.Int32).alias('demand_spike_int'))
    
    # Feature 11: log_current_stock
    exprs.append(pl.col('current_stock').clip(lower_bound=0).log1p().alias('log_current_stock'))
    
    # Apply all expressions
    df = df.with_columns(exprs)
    
    # Feature 1: warehouse_encoded (label encoded via sklearn)
    le = LabelEncoder()
    if 'warehouse_id' in cols:
        warehouse_encoded = le.fit_transform(df['warehouse_id'].to_numpy().astype(str))
        df = df.with_columns(pl.Series('warehouse_encoded', warehouse_encoded))
    else:
        df = df.with_columns(pl.lit(0).alias('warehouse_encoded'))
        
    feature_cols = [
        'inventory_days', 'avg_delay_days', 'warehouse_encoded',
        'stock_to_safety_ratio', 'stock_to_reorder_ratio',
        'demand_volatility', 'is_high_stock', 'delay_risk',
        'total_delays', 'total_spikes', 'demand_spike_int',
        'excess_stock', 'log_current_stock', 'inventory_pressure'
    ]
    
    # Ensure numeric types and fill nulls for features and target
    df = df.with_columns([
        pl.col(c).cast(pl.Float64, strict=False).fill_null(0.0).fill_nan(0.0) for c in feature_cols
    ])
    
    target = 'avg_daily_sales'
    df = df.with_columns(pl.col(target).cast(pl.Float64, strict=False).fill_null(0.0).fill_nan(0.0))
    
    print(f"  Created {len(feature_cols)} features")
    if is_pandas:
        df = df.to_pandas()
    return df, feature_cols, target, le

def train_model(X_pd, y_pd):
    """Train XGBoost regression model with evaluation"""
    print("Training XGBoost Regressor...")
    
    X_train, X_test, y_train, y_test = train_test_split(X_pd, y_pd, test_size=0.2, random_state=42)
    
    model = xgb.XGBRegressor(
        n_estimators=100,
        learning_rate=0.1,
        max_depth=5,
        min_child_weight=3,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42
    )
    
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)
    
    # Evaluation
    predictions = model.predict(X_test)
    mae = mean_absolute_error(y_test, predictions)
    rmse = np.sqrt(mean_squared_error(y_test, predictions))
    r2 = r2_score(y_test, predictions) if len(y_test) > 1 else 0.0
    
    print("Generating SHAP explainability...")
    explainer = shap.Explainer(model, X_train)
    shap_values = explainer(X_test)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Save SHAP summary plot
    plt.figure(figsize=(10, 8))
    shap.summary_plot(shap_values, X_test, show=False)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'shap_summary.png'))
    plt.close()
    
    # Save SHAP feature importance plot
    plt.figure(figsize=(10, 8))
    shap.plots.bar(shap_values, show=False)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'shap_importance.png'))
    plt.close()
    
    # MAPE (handle zeros)
    mask = y_test != 0
    if mask.any():
        mape = np.mean(np.abs((y_test[mask] - predictions[mask]) / y_test[mask])) * 100
    else:
        mape = 0.0
    
    metrics = {
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "r2": round(r2, 4),
        "mape": round(mape, 2),
        "n_features": X_pd.shape[1],
        "n_samples": len(X_pd),
        "trained_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    print(f"\n  Model Evaluation:")
    print(f"    MAE:  {mae:.4f}")
    print(f"    RMSE: {rmse:.4f}")
    print(f"    R²:   {r2:.4f}")
    print(f"    MAPE: {mape:.2f}%")
    
    return model, metrics

def main():
    print("=" * 60)
    print("Supply Chain Demand Forecasting ML Pipeline v2 (Polars Engine)")
    print("=" * 60)
    
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # 1. Load dataset with Polars
        df = load_data(INPUT_FILE)
        
        if df.height == 0:
            print("Error: Dataset is empty. Cannot train model.")
            return

        # 2. Engineer features with Polars
        df, feature_cols, target, le = engineer_features(df)
        
        # Convert to Pandas only at the very end for XGBoost/Scikit-Learn
        X_pd = df.select(feature_cols).to_pandas()
        y_pd = df.select(target).to_pandas()[target]
        
        # 3. Train model
        model, metrics = train_model(X_pd, y_pd)
        
        # 4. Save model
        with open(MODEL_FILE, 'wb') as f:
            pickle.dump({'model': model, 'features': feature_cols, 'label_encoder': le}, f)
        print(f"\n  Model saved to {MODEL_FILE}")
        
        with open(METRICS_FILE, 'w') as f:
            json.dump(metrics, f, indent=2)
        print(f"  Metrics saved to {METRICS_FILE}")
        
        # 5. Predict demand for all records
        print("\nPredicting demand for all records...")
        predicted = model.predict(X_pd)
        # Add predictions back to Polars DataFrame
        df = df.with_columns(pl.Series("predicted_demand", predicted).clip(lower_bound=0.01))
        
        # Calculate days_until_stockout
        print("Calculating stockout risk...")
        df = df.with_columns(
            (pl.col('current_stock') / pl.col('predicted_demand')).alias('days_until_stockout')
        )
        
        # 6. Save output
        drop_cols = [c for c in ['warehouse_encoded', 'stock_to_safety_ratio', 'stock_to_reorder_ratio',
                                  'demand_volatility', 'is_high_stock', 'delay_risk', 'demand_spike_int',
                                  'excess_stock', 'log_current_stock', 'inventory_pressure'] if c in df.columns]
        
        output_df = df.drop(drop_cols)
        output_df.write_csv(OUTPUT_FILE)
        
        print(f"\n{'='*60}")
        print("PIPELINE SUMMARY")
        print(f"{'='*60}")
        print(f"  Total predictions: {output_df.height}")
        print(f"  Average predicted demand: {output_df.select(pl.col('predicted_demand').mean()).item():.2f}")
        print(f"  Average days until stockout: {output_df.select(pl.col('days_until_stockout').mean()).item():.2f}")
        print(f"  Features used: {len(feature_cols)}")
        print(f"  Output saved to: {OUTPUT_FILE}")
        print("=" * 60)
        print("Forecasting pipeline completed successfully using Polars!")

    except Exception as e:
        print(f"Error during pipeline execution: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
