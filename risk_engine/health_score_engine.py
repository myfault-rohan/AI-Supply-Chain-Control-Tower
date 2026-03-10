import pandas as pd
import os

def calculate_health(row):
    """Calculate health status and score based on days until stockout"""
    days = row['days_until_stockout']
    
    if days < 3:
        return "CRITICAL", 20
    elif 3 <= days <= 7:
        return "WARNING", 60
    else:
        return "GOOD", 100

def main():
    input_file = 'dataset/reorder_recommendations.csv'
    output_file = 'dataset/supply_chain_health.csv'
    
    print("-" * 50)
    print("🚀 Supply Chain Health Score Engine")
    print("-" * 50)
    
    if not os.path.exists(input_file):
        print(f"Error: Input file {input_file} not found.")
        return

    # Load data
    print(f"Loading data from {input_file}...")
    df = pd.read_csv(input_file)
    
    if df.empty:
        print("Dataframe is empty. Nothing to calculate.")
        return

    # Apply health logic
    print("Calculating health statuses and scores...")
    health_data = df.apply(calculate_health, axis=1)
    df['health_status'], df['health_score'] = zip(*health_data)
    
    # Select final columns as requested
    output_columns = [
        'product_id', 'current_stock', 'predicted_demand', 
        'days_until_stockout', 'reorder_quantity', 
        'health_status', 'health_score'
    ]
    final_df = df[output_columns]
    
    # Save results
    print(f"Saving results to {output_file}...")
    final_df.to_csv(output_file, index=False)
    
    # Summary report
    print("\n✅ Health Scoring Complete!")
    print("-" * 50)
    print(df['health_status'].value_counts())
    print("-" * 50)

if __name__ == "__main__":
    main()
