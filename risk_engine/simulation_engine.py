import pandas as pd
import os

def simulate_supply_chain(demand_increase_percent, supplier_delay_days):
    """
    Simulates the impact of demand spikes and delivery delays on the supply chain.
    """
    health_file = 'dataset/supply_chain_health.csv'
    reorder_file = 'dataset/reorder_recommendations.csv'
    
    if not os.path.exists(health_file) or not os.path.exists(reorder_file):
        print("Required datasets not found. Please run the health and risk engines first.")
        return None

    # Load data
    df_health = pd.read_csv(health_file)
    df_reorder = pd.read_csv(reorder_file)
    
    # Merge to get lead time data
    df = pd.merge(
        df_health, 
        df_reorder[['product_id', 'supplier_lead_time']], 
        on='product_id', 
        how='left'
    )

    # 1. Increase predicted_demand
    demand_multiplier = 1 + (demand_increase_percent / 100)
    df['sim_predicted_demand'] = df['predicted_demand'] * demand_multiplier

    # 2. Decrease days_until_stockout based on new demand and supplier delay
    # Logic: days_until_stockout = current_stock / new_predicted_demand
    df['sim_days_until_stockout'] = df['current_stock'] / df['sim_predicted_demand']
    
    # 3. Adjust reorder_quantity
    # Standard formula: (demand * lead_time) - stock
    # Lead time is now (baseline + delay)
    sim_lead_time = df['supplier_lead_time'] + supplier_delay_days
    df['sim_reorder_quantity'] = (df['sim_predicted_demand'] * sim_lead_time) - df['current_stock']
    df['sim_reorder_quantity'] = df['sim_reorder_quantity'].apply(lambda x: max(0, x))

    # 4. Recalculate health_status
    def get_health_status(days):
        if days < 3: return "CRITICAL"
        elif 3 <= days <= 7: return "WARNING"
        else: return "GOOD"

    df['sim_health_status'] = df['sim_days_until_stockout'].apply(get_health_status)

    # Return summary statistics
    summary = {
        "total_products": len(df),
        "critical_products": len(df[df['sim_health_status'] == "CRITICAL"]),
        "warning_products": len(df[df['sim_health_status'] == "WARNING"]),
        "good_products": len(df[df['sim_health_status'] == "GOOD"]),
        "total_reorder_quantity": int(df['sim_reorder_quantity'].sum())
    }
    
    return summary

def main():
    print("-" * 50)
    print("📈 SUPPLY CHAIN STRESS TEST SIMULATION")
    print("-" * 50)
    
    # Test case: 25% demand spike, 2 days supplier delay
    demand_spike = 25
    delay = 2
    
    print(f"Scenario: {demand_spike}% Demand Increase, {delay} Days Supplier Delay")
    
    results = simulate_supply_chain(demand_spike, delay)
    
    if results:
        print("\nSimulation Results (Summary Statistics):")
        for key, value in results.items():
            print(f"• {key.replace('_', ' ').capitalize()}: {value}")
        print("-" * 50)

if __name__ == "__main__":
    main()
