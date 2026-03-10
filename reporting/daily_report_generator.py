import pandas as pd
import os
from datetime import datetime

def generate_daily_report():
    """Generates a daily supply chain risk report by consolidating multiple datasets."""
    
    # Define paths
    datasets = {
        "risk_summary": "dataset/global_risk_summary.csv",
        "health": "dataset/supply_chain_health.csv",
        "supplier": "dataset/supplier_performance.csv",
        "warehouse": "dataset/warehouse_utilization.csv",
        "cost": "dataset/cost_analysis.csv"
    }
    
    output_dir = "reports"
    output_file = os.path.join(output_dir, "daily_supply_chain_report.csv")
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    print("--- Daily Supply Chain Risk Report Generator ---")
    
    # 1. Load Summary Data
    summary_msg = ""
    if os.path.exists(datasets["risk_summary"]):
        risk_df = pd.read_csv(datasets["risk_summary"])
        summary_msg = f"""
TOTAL RISK OVERVIEW:
- Critical Products: {risk_df['critical_products'][0]}
- Unreliable Suppliers: {risk_df['unreliable_suppliers'][0]}
- Overloaded Warehouses: {risk_df['overloaded_warehouses'][0]}
- High Cost Impact Items: {risk_df['high_cost_products'][0]}
"""
    else:
        summary_msg = "Risk summary data missing."
    
    print(summary_msg)

    # 2. Extract Top 5 Critical Products
    top_critical = pd.DataFrame()
    if os.path.exists(datasets["health"]):
        health_df = pd.read_csv(datasets["health"])
        top_critical = health_df[health_df['health_status'] == 'CRITICAL'].sort_values(by='days_until_stockout').head(5)
    
    # 3. Extract Top 5 Unreliable Suppliers
    top_suppliers = pd.DataFrame()
    if os.path.exists(datasets["supplier"]):
        supplier_df = pd.read_csv(datasets["supplier"])
        top_suppliers = supplier_df.sort_values(by='reliability_score').head(5)
        
    # 4. Extract Top 5 High Cost Products
    top_costs = pd.DataFrame()
    if os.path.exists(datasets["cost"]):
        cost_df = pd.read_csv(datasets["cost"])
        top_costs = cost_df.sort_values(by='total_cost_impact', ascending=False).head(5)

    # 5. Combine and Save a "Flat" Report for Daily Tracking
    # Since these are different shapes, we'll save them as sections in a CSV or just log them.
    # For a useful CSV, we'll create a structured summary.
    
    report_data = {
        "Report Date": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        "Critical Products Count": [len(top_critical) if not top_critical.empty else 0],
        "Top Critical Item": [top_critical['product_id'].iloc[0] if not top_critical.empty else "N/A"],
        "Top Cost Impact Item": [top_costs['product_id'].iloc[0] if not top_costs.empty else "N/A"],
        "Worst Supplier": [top_suppliers['supplier_id'].iloc[0] if not top_suppliers.empty else "N/A"]
    }
    
    report_df = pd.DataFrame(report_data)
    report_df.to_csv(output_file, index=False)
    
    print(f"Report saved to: {output_file}")
    
    if not top_critical.empty:
        print("\nTOP 5 CRITICAL PRODUCTS:")
        print(top_critical[['product_id', 'days_until_stockout']])
        
    if not top_suppliers.empty:
        print("\nTOP 5 UNRELIABLE SUPPLIERS:")
        print(top_suppliers[['supplier_id', 'reliability_score']])
        
    if not top_costs.empty:
        print("\nTOP 5 HIGH COST PRODUCTS:")
        print(top_costs[['product_id', 'total_cost_impact']])

if __name__ == "__main__":
    generate_daily_report()
