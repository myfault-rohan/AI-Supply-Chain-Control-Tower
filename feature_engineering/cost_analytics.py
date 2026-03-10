import pandas as pd
import os

def perform_cost_analysis():
    """Performs supply chain cost analytics based on demand predictions and inventory."""
    input_file = "dataset/demand_predictions.csv"
    output_file = "dataset/cost_analysis.csv"

    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    # 1. Load dataset
    df = pd.read_csv(input_file)

    # Constants
    HOLDING_COST_PER_UNIT = 2
    STOCKOUT_COST_PER_UNIT = 5

    # 2. Calculate inventory_holding_cost
    df['inventory_holding_cost'] = df['current_stock'] * HOLDING_COST_PER_UNIT

    # 3. Estimate stockout_cost
    # If days_until_stockout < 5, stockout_cost = predicted_demand * 5, else 0
    df['stockout_cost'] = df.apply(
        lambda row: (row['predicted_demand'] * STOCKOUT_COST_PER_UNIT) if row['days_until_stockout'] < 5 else 0,
        axis=1
    )

    # 4. Calculate total_cost_impact
    df['total_cost_impact'] = df['inventory_holding_cost'] + df['stockout_cost']

    # 5. Prepare output
    output_columns = [
        'product_id', 
        'inventory_holding_cost', 
        'stockout_cost', 
        'total_cost_impact'
    ]
    cost_analysis_df = df[output_columns]

    # 6. Save results
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    cost_analysis_df.to_csv(output_file, index=False)
    
    print(f"Cost analysis saved to {output_file}")
    print("\nSample Results:")
    print(cost_analysis_df.head())

if __name__ == "__main__":
    perform_cost_analysis()
