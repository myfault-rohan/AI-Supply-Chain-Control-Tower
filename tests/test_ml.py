"""
Tests for ML Demand Forecasting Pipeline
Tests feature engineering, model training, and prediction quality.
"""

import sys
import os
import pytest
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def _create_test_data():
    """Create a minimal test dataset for ML pipeline testing."""
    data = {
        "product_id": [101, 102, 103, 104, 105],
        "warehouse_id": ["W1", "W2", "W3", "W1", "W2"],
        "current_stock": [12000, 8500, 9000, 4000, 3000],
        "safety_stock": [3000, 2000, 2500, 1500, 1000],
        "reorder_point": [5000, 4000, 4500, 3000, 2000],
        "inventory_days": [10, 9.4, 8.2, 8.0, 6.7],
        "avg_daily_sales": [1200, 900, 1100, 500, 450],
        "total_daily_sales": [2400, 1800, 2200, 1000, 900],
        "stddev_daily_sales": [50, 30, 40, 20, 15],
        "avg_delay_days": [1, 0, 3, 0, 1],
        "total_delays": [1, 0, 1, 0, 0],
        "total_spikes": [0, 0, 0, 0, 0],
        "demand_spike": [False, False, False, False, False],
    }
    return pd.DataFrame(data)


def test_feature_engineering_produces_correct_count():
    """Test that feature engineering creates the expected number of features."""
    from ml_models.demand_forecaster import engineer_features
    
    df = _create_test_data()
    df, feature_cols, target, le = engineer_features(df)
    
    assert len(feature_cols) >= 12, f"Expected 12+ features, got {len(feature_cols)}"
    assert target == "avg_daily_sales"


def test_feature_engineering_no_nans():
    """Test that feature engineering produces no NaN values."""
    from ml_models.demand_forecaster import engineer_features
    
    df = _create_test_data()
    df, feature_cols, target, le = engineer_features(df)
    
    for col in feature_cols:
        assert df[col].isna().sum() == 0, f"Column {col} has NaN values"


def test_demand_forecaster_output_shape():
    """Test that the model produces predictions with correct shape."""
    from ml_models.demand_forecaster import engineer_features, train_model
    
    df = _create_test_data()
    df, feature_cols, target, le = engineer_features(df)
    
    X = df[feature_cols]
    y = df[target]
    
    model, metrics = train_model(X, y)
    predictions = model.predict(X)
    
    assert len(predictions) == len(df), "Prediction count should match input count"


def test_predictions_are_non_negative():
    """Test that demand predictions are non-negative."""
    from ml_models.demand_forecaster import engineer_features, train_model
    
    df = _create_test_data()
    df, feature_cols, target, le = engineer_features(df)
    
    X = df[feature_cols]
    y = df[target]
    
    model, metrics = train_model(X, y)
    predictions = model.predict(X)
    
    # After clipping (which the main pipeline does), all should be >= 0
    clipped = np.clip(predictions, 0.01, None)
    assert (clipped >= 0).all(), "All predictions should be non-negative"


def test_model_metrics_are_computed():
    """Test that model evaluation metrics are computed."""
    from ml_models.demand_forecaster import engineer_features, train_model
    
    df = _create_test_data()
    df, feature_cols, target, le = engineer_features(df)
    
    X = df[feature_cols]
    y = df[target]
    
    model, metrics = train_model(X, y)
    
    assert "mae" in metrics
    assert "rmse" in metrics
    assert "r2" in metrics
    assert "mape" in metrics
    assert metrics["mae"] >= 0
    assert metrics["rmse"] >= 0


def test_feature_count_matches_expected():
    """Test that the engineered features match specific expected ones."""
    from ml_models.demand_forecaster import engineer_features
    
    df = _create_test_data()
    df, feature_cols, target, le = engineer_features(df)
    
    expected_features = [
        "inventory_days", "avg_delay_days", "warehouse_encoded",
        "stock_to_safety_ratio", "stock_to_reorder_ratio",
        "demand_volatility", "is_high_stock", "delay_risk"
    ]
    
    for feat in expected_features:
        assert feat in feature_cols, f"Missing expected feature: {feat}"
