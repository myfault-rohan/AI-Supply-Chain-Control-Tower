"""
Supply Chain Demand Forecasting Pipeline
Trains an XGBoost model to predict daily sales and calculates stockout risk.
"""

import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import os

# Configuration
INPUT_FILE = 'dataset/processed_supply_chain.csv'
OUTPUT_FILE = 'dataset/demand_predictions.csv'

def load_data(filepath):
    """Load the processed supply chain dataset"""
    print(f"Loading data from {filepath}...")
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Dataset not found at {filepath}")
    
    df = pd.read_csv(filepath)
    print(f"Loaded {len(df)} records.")
    return df

def preprocess_data(df):
    """Preprocess features for training"""
    print("Preprocessing data...")
    
    # Define features and target based on user requirements
    # 'delay_days' in user request maps to 'avg_delay_days' in our dataset
    # 'daily_sales' in user request maps to 'avg_daily_sales' in our dataset
    features = ['inventory_days', 'avg_delay_days', 'warehouse_id']
    target = 'avg_daily_sales'
    
    # Handle missing values if any
    df = df.fillna(0)
    
    # Encoding categorical feature: warehouse_id
    le = LabelEncoder()
    df['warehouse_encoded'] = le.fit_transform(df['warehouse_id'])
    
    X = df[['inventory_days', 'avg_delay_days', 'warehouse_encoded']]
    y = df[target]
    
    return X, y, df, le

def train_model(X, y):
    """Train XGBoost regression model"""
    print("Splitting data into training and testing sets...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("Training XGBoost Regressor...")
    model = xgb.XGBRegressor(
        n_estimators=100,
        learning_rate=0.1,
        max_depth=5,
        random_state=42
    )
    
    model.fit(X_train, y_train)
    
    # Evaluation
    predictions = model.predict(X_test)
    mae = mean_absolute_error(y_test, predictions)
    rmse = np.sqrt(mean_squared_error(y_test, predictions))
    r2 = r2_score(y_test, predictions)
    
    print(f"Model Evaluation:")
    print(f"  MAE:  {mae:.4f}")
    print(f"  RMSE: {rmse:.4f}")
    print(f"  R2:   {r2:.4f}")
    
    return model

def main():
    print("=" * 60)
    print("Supply Chain Demand Forecasting ML Pipeline")
    print("=" * 60)
    
    try:
        # 1. Load dataset
        df = load_data(INPUT_FILE)
        
        if len(df) == 0:
            print("Error: Dataset is empty. Cannot train model.")
            return

        # 2. Preprocess and split
        X, y, original_df, le = preprocess_data(df)
        
        # 3. Train XGBoost model
        model = train_model(X, y)
        
        # 4. Predict future demand (on the whole dataset for visualization/output)
        print("\nPredicting demand for all records...")
        original_df['predicted_demand'] = model.predict(X)
        
        # Avoid zero division and negative predictions
        original_df['predicted_demand'] = original_df['predicted_demand'].clip(lower=0.01)
        
        # Calculate days_until_stockout = current_stock / predicted_demand
        print("Calculating stockout risk...")
        original_df['days_until_stockout'] = original_df['current_stock'] / original_df['predicted_demand']
        
        # 5. Save output dataset
        print(f"Saving predictions to {OUTPUT_FILE}...")
        # Drop the temporary encoding column before saving
        output_df = original_df.drop(columns=['warehouse_encoded'])
        output_df.to_csv(OUTPUT_FILE, index=False)
        
        print("\n" + "=" * 60)
        print("PIPELINE SUMMARY")
        print("=" * 60)
        print(f"Total predictions: {len(output_df)}")
        print(f"Average predicted demand: {output_df['predicted_demand'].mean():.2f}")
        print(f"Average days until stockout: {output_df['days_until_stockout'].mean():.2f}")
        print(f"Output saved to: {OUTPUT_FILE}")
        print("=" * 60)
        print("Forecasting pipeline completed successfully!")

    except Exception as e:
        print(f"Error during pipeline execution: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
