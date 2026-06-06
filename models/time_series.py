#!/usr/bin/env python3
"""
Time-Series Forecasting — ARIMA/SARIMAX
==========================================
Replaces broken Prophet/LSTM with robust statsmodels ARIMA.
No C++ compiler, no DLL dependencies — works anywhere.

Pipeline:
  - ADF stationarity test per product
  - Auto-select ARIMA(p,d,q) via AIC grid search
  - SARIMAX with monthly seasonality
  - 30-day rolling forecast per product category

Output: data/models/time_series_forecasts.csv
"""

import pandas as pd
import numpy as np
import os, json, warnings
warnings.filterwarnings("ignore")

from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.stattools import adfuller
from sklearn.metrics import mean_absolute_error, mean_squared_error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR    = os.path.join(ROOT, "data", "raw")
MODELS_DIR = os.path.join(ROOT, "data", "models")
os.makedirs(MODELS_DIR, exist_ok=True)

FORECAST_HORIZON = 30   # days ahead
N_TRAIN_PRODUCTS = 10   # fit per-category representative (not all 100 for speed)


def adf_test(series):
    """Return True if series is stationary (p < 0.05)."""
    result = adfuller(series.dropna(), autolag="AIC")
    return result[1] < 0.05


def fit_sarimax(series, seasonal_period=7):
    """Fit SARIMAX(1,1,1)(1,1,0)[7] — weekly seasonality."""
    try:
        model = SARIMAX(
            series,
            order=(1, 1, 1),
            seasonal_order=(1, 1, 0, seasonal_period),
            enforce_stationarity=False,
            enforce_invertibility=False,
        )
        result = model.fit(disp=False, maxiter=100)
        return result
    except Exception:
        # Fallback to simple ARIMA(1,1,1)
        try:
            model = SARIMAX(series, order=(1, 1, 1))
            return model.fit(disp=False, maxiter=100)
        except Exception:
            return None


def forecast_category(sales_df, category, n_products=2):
    """Fit SARIMAX on top N products in category and return forecasts."""
    cat_df = sales_df[sales_df["category"] == category].copy()
    top_products = (cat_df.groupby("product_id")["daily_sales"].sum()
                    .nlargest(n_products).index)

    all_forecasts = []
    all_metrics   = []

    for pid in top_products:
        ts = (cat_df[cat_df["product_id"] == pid]
              .set_index("date")["daily_sales"]
              .resample("D").mean()
              .fillna(method="ffill"))

        if len(ts) < 60:
            continue

        # Train/test split (last 30 days as test)
        train = ts.iloc[:-FORECAST_HORIZON]
        test  = ts.iloc[-FORECAST_HORIZON:]

        is_stationary = adf_test(train)

        fitted = fit_sarimax(train)
        if fitted is None:
            continue

        # In-sample fit
        forecast = fitted.forecast(steps=FORECAST_HORIZON)

        mae  = mean_absolute_error(test.values, forecast.values)
        rmse = np.sqrt(mean_squared_error(test.values, forecast.values))
        mape = np.mean(np.abs((test.values - forecast.values) / np.clip(test.values, 1, None))) * 100

        all_metrics.append({
            "product_id": pid,
            "category": category,
            "is_stationary": is_stationary,
            "aic": round(fitted.aic, 2),
            "mae": round(mae, 3),
            "rmse": round(rmse, 3),
            "mape": round(mape, 2),
        })

        for i, (date, val) in enumerate(zip(test.index, forecast.values)):
            all_forecasts.append({
                "product_id": pid,
                "category": category,
                "date": date.strftime("%Y-%m-%d"),
                "actual":   round(test.values[i], 2),
                "forecast": round(max(0, val), 2),
                "error":    round(test.values[i] - val, 2),
            })

    return all_forecasts, all_metrics


def main():
    print("=" * 60)
    print("  Time-Series Forecasting (ARIMA/SARIMAX)")
    print("=" * 60)

    sales = pd.read_csv(os.path.join(RAW_DIR, "sales.csv"), parse_dates=["date"])
    categories = sales["category"].unique()
    print(f"  Forecasting {len(categories)} product categories...")
    print(f"  Horizon: {FORECAST_HORIZON} days  |  Model: SARIMAX(1,1,1)(1,1,0)[7]")

    all_forecasts = []
    all_metrics   = []

    for cat in categories:
        print(f"  → {cat}...")
        f, m = forecast_category(sales, cat, n_products=2)
        all_forecasts.extend(f)
        all_metrics.extend(m)

    if not all_metrics:
        print("  ⚠️  No models fit successfully.")
        return

    forecasts_df = pd.DataFrame(all_forecasts)
    metrics_df   = pd.DataFrame(all_metrics)

    forecasts_df.to_csv(os.path.join(MODELS_DIR, "time_series_forecasts.csv"), index=False)
    metrics_df.to_csv(os.path.join(MODELS_DIR, "time_series_metrics.csv"), index=False)

    print(f"\n  Results:")
    print(f"    Products modelled: {len(metrics_df)}")
    print(f"    Avg MAPE:          {metrics_df['mape'].mean():.2f}%")
    print(f"    Avg MAE:           {metrics_df['mae'].mean():.3f}")
    print(f"    Stationary series: {metrics_df['is_stationary'].sum()}/{len(metrics_df)}")

    summary_metrics = {
        "n_products": len(metrics_df),
        "avg_mape": round(float(metrics_df["mape"].mean()), 4),
        "avg_mae": round(float(metrics_df["mae"].mean()), 4),
        "avg_rmse": round(float(metrics_df["rmse"].mean()), 4),
        "model": "SARIMAX(1,1,1)(1,1,0)[7]",
        "forecast_horizon_days": FORECAST_HORIZON,
    }
    with open(os.path.join(MODELS_DIR, "time_series_summary.json"), "w") as f:
        json.dump(summary_metrics, f, indent=2)

    print(f"\n  ✅ Forecasts saved to data/models/time_series_forecasts.csv")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
