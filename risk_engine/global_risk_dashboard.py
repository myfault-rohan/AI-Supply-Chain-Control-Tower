import pandas as pd
import os

def aggregate_global_risks():
    """Aggregates supply chain risks from multiple datasets into a summary."""
    health_file = "dataset/supply_chain_health.csv"
    supplier_file = "dataset/supplier_performance.csv"
    warehouse_file = "dataset/warehouse_utilization.csv"
    cost_file = "dataset/cost_analysis.csv"
    output_file = "dataset/global_risk_summary.csv"

    # Initialize counts
    critical_products = 0
    unreliable_suppliers = 0
    overloaded_warehouses = 0
    high_cost_products = 0

    # 1. Count critical stockout products
    if os.path.exists(health_file):
        health_df = pd.read_csv(health_file)
        critical_products = len(health_df[health_df['health_status'] == 'CRITICAL'])

    # 2. Count unreliable suppliers
    if os.path.exists(supplier_file):
        supplier_df = pd.read_csv(supplier_file)
        unreliable_suppliers = len(supplier_df[supplier_df['supplier_status'] == 'CRITICAL'])

    # 3. Count overloaded warehouses
    if os.path.exists(warehouse_file):
        warehouse_df = pd.read_csv(warehouse_file)
        overloaded_warehouses = len(warehouse_df[warehouse_df['status'] == 'HIGH'])

    # 4. Count high cost impact products
    if os.path.exists(cost_file):
        cost_df = pd.read_csv(cost_file)
        high_cost_products = len(cost_df[cost_df['total_cost_impact'] > 500])

    # Create summary dataset
    summary_data = {
        "critical_products": [critical_products],
        "unreliable_suppliers": [unreliable_suppliers],
        "overloaded_warehouses": [overloaded_warehouses],
        "high_cost_products": [high_cost_products]
    }
    summary_df = pd.DataFrame(summary_data)

    # Save results
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    summary_df.to_csv(output_file, index=False)
    
    print(f"Global risk summary saved to {output_file}")
    print("\nRisk Summary:")
    print(summary_df)

if __name__ == "__main__":
    aggregate_global_risks()
