"""
Reorder Optimization Engine
Calculates reorder quantities and detects stockout risks based on demand forecasting.
"""

import pandas as pd
import numpy as np
import os

# Configuration
DEMAND_FILE = 'dataset/demand_predictions.csv'
SHIPMENTS_FILE = 'dataset/shipments.csv'
SUPPLIERS_FILE = 'dataset/suppliers.csv'
OUTPUT_FILE = 'dataset/reorder_recommendations.csv'

def load_data():
    """Load all necessary datasets"""
    print("Loading datasets...")
    files = [DEMAND_FILE, SHIPMENTS_FILE, SUPPLIERS_FILE]
    for f in files:
        if not os.path.exists(f):
            raise FileNotFoundError(f"Required file not found: {f}")
    
    demand_df = pd.read_csv(DEMAND_FILE)
    shipments_df = pd.read_csv(SHIPMENTS_FILE)
    suppliers_df = pd.read_csv(SUPPLIERS_FILE)
    
    return demand_df, shipments_df, suppliers_df

def get_supplier_lead_times(shipments_df, suppliers_df):
    """Calculate average lead time for each product based on historical shipments"""
    print("Calculating lead times per product...")
    
    # Merge shipments with suppliers to get lead times
    merged = shipments_df.merge(suppliers_df[['supplier_id', 'lead_time_days']], on='supplier_id', how='left')
    
    # Group by product to get average lead time
    # In a real scenario, this would be more complex, but we'll use the supplier's stated lead time
    product_lead_times = merged.groupby('product_id')['lead_time_days'].mean().reset_index()
    product_lead_times.rename(columns={'lead_time_days': 'supplier_lead_time'}, inplace=True)
    
    return product_lead_times

def optimize_reorders(demand_df, lead_times_df):
    """Calculate reorder quantities and risk alerts"""
    print("Optimizing reorders...")
    
    # Merge demand predictions with lead times
    df = demand_df.merge(lead_times_df, on='product_id', how='left')
    
    # Fill missing lead times with a default (e.g., 7 days)
    df['supplier_lead_time'] = df['supplier_lead_time'].fillna(7)
    
    # 1. Calculate reorder_quantity
    # Formula: (predicted_demand * supplier_lead_time) + safety_stock - current_stock
    df['reorder_quantity'] = (
        (df['predicted_demand'] * df['supplier_lead_time']) + 
        df['safety_stock'] - 
        df['current_stock']
    )
    
    # Quantities should not be negative
    df['reorder_quantity'] = df['reorder_quantity'].clip(lower=0).round(0)
    
    # 2. Detect stockout risk
    # Risk if days_until_stockout < supplier_lead_time
    df['stockout_risk'] = df['days_until_stockout'] < df['supplier_lead_time']
    
    # 3. Generate alert messages
    def create_alert(row):
        if row['stockout_risk']:
            return f"Product {row['product_id']} will stockout in {row['days_until_stockout']:.0f} days. Reorder immediately."
        elif row['reorder_quantity'] > 0:
            return f"Product {row['product_id']} reorder recommended. Quantity: {row['reorder_quantity']:.0f}."
        else:
            return f"Product {row['product_id']} stock level healthy."
            
    df['alert_message'] = df.apply(create_alert, axis=1)
    
    return df

def main():
    print("=" * 60)
    print("Supply Chain Reorder Optimization Engine")
    print("=" * 60)
    
    try:
        # Load data
        demand_df, shipments_df, suppliers_df = load_data()
        
        # Process lead times
        lead_times_df = get_supplier_lead_times(shipments_df, suppliers_df)
        
        # Optimize
        recommendations_df = optimize_reorders(demand_df, lead_times_df)
        
        # Save results
        print(f"Saving recommendations to {OUTPUT_FILE}...")
        recommendations_df.to_csv(OUTPUT_FILE, index=False)
        
        # Summary
        risky_items = recommendations_df[recommendations_df['stockout_risk'] == True]
        print("\n" + "=" * 60)
        print("OPTIMIZATION SUMMARY")
        print("=" * 60)
        print(f"Total items analyzed: {len(recommendations_df)}")
        print(f"Items with stockout risk: {len(risky_items)}")
        print(f"Total reorder recommendations: {len(recommendations_df[recommendations_df['reorder_quantity'] > 0])}")
        print(f"Output saved to: {OUTPUT_FILE}")
        print("=" * 60)
        print("Optimization complete!")

    except Exception as e:
        print(f"Error during optimization: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
