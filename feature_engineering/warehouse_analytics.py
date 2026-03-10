import pandas as pd
import os

def analyze_warehouse_utilization():
    """Analyzes warehouse utilization by merging inventory and capacity data."""
    inventory_file = "dataset/inventory.csv"
    warehouses_file = "dataset/warehouses.csv"
    output_file = "dataset/warehouse_utilization.csv"

    if not os.path.exists(inventory_file) or not os.path.exists(warehouses_file):
        print("Error: Required input files missing.")
        return

    # 1. Load datasets
    inventory_df = pd.read_csv(inventory_file)
    warehouses_df = pd.read_csv(warehouses_file)

    # 2. Calculate total stock per warehouse
    stock_per_warehouse = inventory_df.groupby('warehouse_id')['current_stock'].sum().reset_index()
    stock_per_warehouse.rename(columns={'current_stock': 'total_stock'}, inplace=True)

    # 3. Merge with warehouse metadata
    utilization_df = pd.merge(warehouses_df, stock_per_warehouse, on='warehouse_id', how='left')
    utilization_df['total_stock'] = utilization_df['total_stock'].fillna(0)

    # 4. Calculate utilization percentage
    utilization_df['utilization_percent'] = (utilization_df['total_stock'] / utilization_df['capacity']) * 100

    # 5. Classify warehouse status
    def classify_status(percent):
        if percent > 85:
            return "HIGH"
        elif 40 <= percent <= 85:
            return "NORMAL"
        else:
            return "LOW"

    utilization_df['status'] = utilization_df['utilization_percent'].apply(classify_status)

    # 6. Save results
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    utilization_df.to_csv(output_file, index=False)
    
    print(f"Warehouse utilization analysis saved to {output_file}")
    print("\nResults:")
    print(utilization_df)

if __name__ == "__main__":
    analyze_warehouse_utilization()
