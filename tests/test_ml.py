import os
import pandas as pd
import numpy as np

def test_model_artifacts_exist():
    """Verify that the XGBoost model outputs are present."""
    assert os.path.exists("data/processed/test_scored.parquet")
    assert os.path.exists("data/models/test_shap_values.npy")
    assert os.path.exists("data/models/seller_churn_model.json")

def test_scored_data_schema():
    """Verify the scored dataset contains the required columns."""
    if not os.path.exists("data/processed/test_scored.parquet"):
        return
    df = pd.read_parquet("data/processed/test_scored.parquet")
    assert "seller_id" in df.columns
    assert "churn_probability" in df.columns
    assert "risk_tier" in df.columns
    assert "revenue_at_risk_30d" in df.columns
