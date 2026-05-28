"""
Prophet Time-Series Demand Forecasting
Trains Prophet models for individual products to forecast daily sales.
Compares metrics against XGBoost and outputs to dataset/processed files/
"""

import pandas as pd
import numpy as np
from prophet import Prophet
from sklearn.metrics import mean_absolute_error, mean_squared_error
import os
import json
from datetime import datetime

# Configuration
INPUT_FILE = 'dataset/synthetic/sales.csv'
OUTPUT_DIR = 'dataset/processed files'
OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'prophet_predictions.csv')
METRICS_FILE = os.path.join(OUTPUT_DIR, 'model_metrics_prophet.json')

def load_data(filepath):
    print(f"Loading sales data from {filepath}...")
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Dataset not found at {filepath}")
    
    df = pd.read_csv(filepath)
    df['date'] = pd.to_datetime(df['date'])
    
    # Aggregate daily sales per product
    daily_sales = df.groupby(['date', 'product_id'])['quantity'].sum().reset_index()
    return daily_sales

def train_and_evaluate(df):
    """Train Prophet on each product and evaluate on the last 14 days."""
    results = []
    metrics = []
    
    products = df['product_id'].unique()
    print(f"Training Prophet models for {len(products)} products...")
    
    for i, product in enumerate(products):
        pdf = df[df['product_id'] == product].copy()
        pdf = pdf.rename(columns={'date': 'ds', 'quantity': 'y'})
        pdf = pdf.sort_values('ds')
        
        if len(pdf) < 30:
            print(f"Skipping {product} (insufficient data: {len(pdf)} rows)")
            continue
            
        # Train-test split (last 14 days as test)
        train = pdf.iloc[:-14]
        test = pdf.iloc[-14:]
        
        model = Prophet(daily_seasonality=True, yearly_seasonality=False, weekly_seasonality=True)
        model.fit(train)
        
        future = model.make_future_dataframe(periods=14)
        forecast = model.predict(future)
        
        # Evaluate
        predictions = forecast.iloc[-14:]['yhat'].values
        actuals = test['y'].values
        
        mae = mean_absolute_error(actuals, predictions)
        rmse = np.sqrt(mean_squared_error(actuals, predictions))
        
        mask = actuals != 0
        mape = np.mean(np.abs((actuals[mask] - predictions[mask]) / actuals[mask])) * 100 if mask.any() else 0.0
        
        metrics.append({
            'product_id': product,
            'mae': mae,
            'rmse': rmse,
            'mape': mape
        })
        
        # Now train on full data for future 30 days forecast
        full_model = Prophet(daily_seasonality=True, yearly_seasonality=False, weekly_seasonality=True)
        full_model.fit(pdf)
        full_future = full_model.make_future_dataframe(periods=30)
        full_forecast = full_model.predict(full_future)
        
        for idx, row in full_forecast.tail(30).iterrows():
            results.append({
                'product_id': product,
                'forecast_date': row['ds'].strftime("%Y-%m-%d"),
                'predicted_demand': max(0.01, row['yhat']),
                'yhat_lower': max(0.01, row['yhat_lower']),
                'yhat_upper': row['yhat_upper']
            })
            
    # Aggregate metrics
    if metrics:
        avg_mae = np.mean([m['mae'] for m in metrics])
        avg_rmse = np.mean([m['rmse'] for m in metrics])
        avg_mape = np.mean([m['mape'] for m in metrics])
    else:
        avg_mae = avg_rmse = avg_mape = 0.0
        
    global_metrics = {
        "mae": round(avg_mae, 4),
        "rmse": round(avg_rmse, 4),
        "mape": round(avg_mape, 2),
        "trained_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "model_type": "Prophet",
        "products_modeled": len(metrics)
    }
    
    print(f"\n  Global Prophet Evaluation:")
    print(f"    MAE:  {avg_mae:.4f}")
    print(f"    RMSE: {avg_rmse:.4f}")
    print(f"    MAPE: {avg_mape:.2f}%")
    
    return pd.DataFrame(results), global_metrics

def main():
    print("=" * 60)
    print("Prophet Demand Forecasting Pipeline")
    print("=" * 60)
    
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        df = load_data(INPUT_FILE)
        
        predictions_df, global_metrics = train_and_evaluate(df)
        
        predictions_df.to_csv(OUTPUT_FILE, index=False)
        print(f"\n  Forecast saved to {OUTPUT_FILE}")
        
        with open(METRICS_FILE, 'w') as f:
            json.dump(global_metrics, f, indent=2)
        print(f"  Metrics saved to {METRICS_FILE}")
        
    except Exception as e:
        print(f"Error during Prophet pipeline: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
