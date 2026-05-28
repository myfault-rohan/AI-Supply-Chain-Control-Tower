"""
Supply Chain Demand Forecasting Pipeline
Trains an XGBoost model to predict daily sales and calculates stockout risk.
Outputs to dataset/processed files/ for consistency with the API layer.

Model Card:
  Model: XGBoost Demand Forecaster v2
  Features: 12 engineered features (inventory, sales, timing, supplier metrics)
  Target: avg_daily_sales
  Last trained: auto-recorded on each run
  Performance: MAE, RMSE, R², MAPE logged to console
"""

import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import os
import json
import pickle
from datetime import datetime
import shap
import matplotlib.pyplot as plt

# Configuration
INPUT_FILE = 'dataset/processed_supply_chain.csv'
OUTPUT_DIR = 'dataset/processed files'
OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'demand_predictions.csv')
MODEL_FILE = os.path.join(OUTPUT_DIR, 'demand_model.pkl')
METRICS_FILE = os.path.join(OUTPUT_DIR, 'model_metrics.json')

def load_data(filepath):
    """Load the processed supply chain dataset"""
    print(f"Loading data from {filepath}...")
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Dataset not found at {filepath}")
    
    df = pd.read_csv(filepath)
    print(f"Loaded {len(df)} records with columns: {list(df.columns)}")
    return df

def engineer_features(df):
    """Create 12+ engineered features for production-quality predictions"""
    print("Engineering features...")
    
    # Ensure required base columns exist with defaults
    if 'avg_daily_sales' not in df.columns:
        df['avg_daily_sales'] = df.get('daily_demand', 1.0)
    if 'avg_delay_days' not in df.columns:
        df['avg_delay_days'] = 0
    if 'inventory_days' not in df.columns and 'current_stock' in df.columns:
        df['inventory_days'] = np.where(
            df['avg_daily_sales'] > 0,
            df['current_stock'] / df['avg_daily_sales'],
            9999
        )
    
    # Feature 1: warehouse_encoded (label encoded)
    le = LabelEncoder()
    if 'warehouse_id' in df.columns:
        df['warehouse_encoded'] = le.fit_transform(df['warehouse_id'].astype(str))
    else:
        df['warehouse_encoded'] = 0
        
    # Feature 2: stock_to_safety_ratio
    if 'safety_stock' in df.columns:
        df['stock_to_safety_ratio'] = np.where(
            df['safety_stock'] > 0,
            df['current_stock'] / df['safety_stock'],
            df['current_stock']
        )
    else:
        df['stock_to_safety_ratio'] = 1.0
    
    # Feature 3: stock_to_reorder_ratio
    if 'reorder_point' in df.columns:
        df['stock_to_reorder_ratio'] = np.where(
            df['reorder_point'] > 0,
            df['current_stock'] / df['reorder_point'],
            df['current_stock']
        )
    else:
        df['stock_to_reorder_ratio'] = 1.0
    
    # Feature 4: demand_volatility (stddev / mean of daily sales)
    if 'stddev_daily_sales' in df.columns:
        df['demand_volatility'] = np.where(
            df['avg_daily_sales'] > 0,
            df['stddev_daily_sales'] / df['avg_daily_sales'],
            0
        )
    else:
        df['demand_volatility'] = 0
    
    # Feature 5: is_high_stock (binary - above reorder point)
    if 'reorder_point' in df.columns:
        df['is_high_stock'] = (df['current_stock'] > df['reorder_point']).astype(int)
    else:
        df['is_high_stock'] = 1
    
    # Feature 6: delay_risk (binary - avg delay > 2 days)
    df['delay_risk'] = (df['avg_delay_days'] > 2).astype(int)
    
    # Feature 7: total_delays count
    if 'total_delays' not in df.columns:
        df['total_delays'] = 0
    
    # Feature 8: total_spikes count
    if 'total_spikes' not in df.columns:
        df['total_spikes'] = 0
    
    # Feature 9: demand_spike (binary)
    if 'demand_spike' not in df.columns:
        df['demand_spike'] = False
    df['demand_spike_int'] = df['demand_spike'].astype(int)
    
    # Feature 10: excess_stock = current_stock - safety_stock
    if 'safety_stock' in df.columns:
        df['excess_stock'] = df['current_stock'] - df['safety_stock']
    else:
        df['excess_stock'] = df['current_stock']
    
    # Feature 11: log_current_stock (log transform for skewed distributions)
    df['log_current_stock'] = np.log1p(df['current_stock'].clip(lower=0))
    
    # Feature 12: inventory_pressure = safety_stock / (current_stock + 1)
    if 'safety_stock' in df.columns:
        df['inventory_pressure'] = df['safety_stock'] / (df['current_stock'] + 1)
    else:
        df['inventory_pressure'] = 0
    
    # Define final feature list
    feature_cols = [
        'inventory_days', 'avg_delay_days', 'warehouse_encoded',
        'stock_to_safety_ratio', 'stock_to_reorder_ratio',
        'demand_volatility', 'is_high_stock', 'delay_risk',
        'total_delays', 'total_spikes', 'demand_spike_int',
        'excess_stock', 'log_current_stock', 'inventory_pressure'
    ]
    
    # Ensure all feature columns exist and fill NaN
    for col in feature_cols:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    target = 'avg_daily_sales'
    df[target] = pd.to_numeric(df[target], errors='coerce').fillna(0)
    
    print(f"  Created {len(feature_cols)} features")
    return feature_cols, target, le

def train_model(X, y):
    """Train XGBoost regression model with evaluation"""
    print("Training XGBoost Regressor...")
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
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
    
    # Ensure output dir exists for SHAP plots
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
        "n_features": X.shape[1],
        "n_samples": len(X),
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
    print("Supply Chain Demand Forecasting ML Pipeline v2")
    print("=" * 60)
    
    try:
        # Ensure output directory exists
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # 1. Load dataset
        df = load_data(INPUT_FILE)
        
        if len(df) == 0:
            print("Error: Dataset is empty. Cannot train model.")
            return

        # 2. Engineer features
        feature_cols, target, le = engineer_features(df)
        
        X = df[feature_cols]
        y = df[target]
        
        # 3. Train model
        model, metrics = train_model(X, y)
        
        # 4. Save model
        with open(MODEL_FILE, 'wb') as f:
            pickle.dump({'model': model, 'features': feature_cols, 'label_encoder': le}, f)
        print(f"\n  Model saved to {MODEL_FILE}")
        
        # Save metrics
        with open(METRICS_FILE, 'w') as f:
            json.dump(metrics, f, indent=2)
        print(f"  Metrics saved to {METRICS_FILE}")
        
        # 5. Predict demand for all records
        print("\nPredicting demand for all records...")
        df['predicted_demand'] = model.predict(X)
        df['predicted_demand'] = df['predicted_demand'].clip(lower=0.01)
        
        # Calculate days_until_stockout
        print("Calculating stockout risk...")
        df['days_until_stockout'] = df['current_stock'] / df['predicted_demand']
        
        # 6. Save output
        # Drop temporary encoding columns before saving
        drop_cols = [c for c in ['warehouse_encoded', 'stock_to_safety_ratio', 'stock_to_reorder_ratio',
                                  'demand_volatility', 'is_high_stock', 'delay_risk', 'demand_spike_int',
                                  'excess_stock', 'log_current_stock', 'inventory_pressure'] if c in df.columns]
        output_df = df.drop(columns=drop_cols, errors='ignore')
        output_df.to_csv(OUTPUT_FILE, index=False)
        
        print(f"\n{'='*60}")
        print("PIPELINE SUMMARY")
        print(f"{'='*60}")
        print(f"  Total predictions: {len(output_df)}")
        print(f"  Average predicted demand: {output_df['predicted_demand'].mean():.2f}")
        print(f"  Average days until stockout: {output_df['days_until_stockout'].mean():.2f}")
        print(f"  Features used: {len(feature_cols)}")
        print(f"  Output saved to: {OUTPUT_FILE}")
        print("=" * 60)
        print("Forecasting pipeline completed successfully!")

    except Exception as e:
        print(f"Error during pipeline execution: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
