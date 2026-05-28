"""
Deep Learning LSTM Demand Forecaster
Uses NeuralForecast (Nixtla) to train an advanced LSTM model for supply chain demand forecasting.
"""

import polars as pl
import pandas as pd
import os
import json
import matplotlib.pyplot as plt
from datetime import datetime

# NeuralForecast imports
from neuralforecast import NeuralForecast
from neuralforecast.models import LSTM
from neuralforecast.losses.pytorch import MAE

INPUT_FILE = 'dataset/synthetic/sales.csv'
OUTPUT_DIR = 'dataset/processed files'
OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'lstm_predictions.csv')
METRICS_FILE = os.path.join(OUTPUT_DIR, 'lstm_metrics.json')
MODEL_DIR = os.path.join(OUTPUT_DIR, 'lstm_model')

def load_data(filepath):
    print(f"Loading data from {filepath} with Polars...")
    df = pl.read_csv(filepath)
    
    # NeuralForecast requires ['unique_id', 'ds', 'y'] format
    daily_sales = df.group_by(['product_id', 'date']).agg(pl.col('daily_sales').sum().alias('y'))
    
    # Rename columns for NeuralForecast
    nf_df = daily_sales.rename({
        "product_id": "unique_id",
        "date": "ds"
    })
    
    pdf = nf_df.to_pandas()
    pdf['ds'] = pd.to_datetime(pdf['ds'])
    pdf = pdf.sort_values(['unique_id', 'ds']).reset_index(drop=True)
    return pdf

def main():
    print("=" * 60)
    print("Supply Chain Deep Learning Forecaster (LSTM)")
    print("=" * 60)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df = load_data(INPUT_FILE)
    
    # Filter for top 5 products to train quickly for demonstration
    top_products = df['unique_id'].value_counts().head(5).index.tolist()
    train_df = df[df['unique_id'].isin(top_products)].copy()
    
    print(f"Training LSTM on {len(top_products)} products...")
    
    horizon = 14 # Predict next 14 days
    
    # Define the LSTM model
    models = [
        LSTM(
            h=horizon,
            max_steps=100,      # Small number of steps for demo
            scaler_type='standard',
            encoder_hidden_size=64,
            decoder_hidden_size=64,
            learning_rate=1e-3,
            loss=MAE()
        )
    ]
    
    nf = NeuralForecast(models=models, freq='D')
    
    print("Fitting model (this may take a moment)...")
    nf.fit(df=train_df)
    
    print("Generating forecasts...")
    forecasts = nf.predict()
    
    # Save forecasts
    forecasts.reset_index(inplace=True)
    forecasts.to_csv(OUTPUT_FILE, index=False)
    
    # Save model
    os.makedirs(MODEL_DIR, exist_ok=True)
    nf.save(path=MODEL_DIR, model_index=None, overwrite=True, save_dataset=False)
    
    # Generate plot for the first product
    sample_product = top_products[0]
    sample_history = train_df[train_df['unique_id'] == sample_product]
    sample_forecast = forecasts[forecasts['unique_id'] == sample_product]
    
    plt.figure(figsize=(12, 6))
    plt.plot(sample_history['ds'].tail(30), sample_history['y'].tail(30), label='History')
    plt.plot(sample_forecast['ds'], sample_forecast['LSTM'], label='LSTM Forecast', linestyle='--')
    plt.title(f"LSTM Forecast for {sample_product}")
    plt.xlabel("Date")
    plt.ylabel("Demand")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'lstm_forecast_sample.png'))
    plt.close()
    
    metrics = {
        "model": "LSTM (NeuralForecast)",
        "horizon": horizon,
        "products_modeled": len(top_products),
        "trained_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    with open(METRICS_FILE, 'w') as f:
        json.dump(metrics, f, indent=2)
        
    print(f"\nSaved forecasts to {OUTPUT_FILE}")
    print(f"Saved model to {MODEL_DIR}")
    print(f"Saved metrics to {METRICS_FILE}")
    print("=" * 60)

if __name__ == "__main__":
    main()
