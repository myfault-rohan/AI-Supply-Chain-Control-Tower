import numpy as np
import pandas as pd

def run_simulation(df, delay_days=0, demand_spike=0, supplier_capacity=100, cost_multiplier=1.0):
    if df.empty:
        return df

    sim_df = df.copy()
    
    # Apply delay
    if 'avg_delay_days' in sim_df.columns:
        sim_df['sim_delay_days'] = sim_df['avg_delay_days'] + delay_days
    else:
        sim_df['sim_delay_days'] = delay_days

    # Apply demand spike
    if 'predicted_demand' in sim_df.columns:
        sim_df['sim_demand'] = sim_df['predicted_demand'] * (1 + demand_spike / 100.0)
    else:
        sim_df['sim_demand'] = 100 * (1 + demand_spike / 100.0)

    # Calculate simulated days until stockout
    sim_df['sim_days_until_stockout'] = np.where(
        sim_df['sim_demand'] > 0,
        sim_df['current_stock'] / sim_df['sim_demand'],
        999
    ).round(1)

    # Calculate financial impact
    # Holding cost = stock * 2.0 * cost_multiplier
    # Stockout cost = demand * 5.0 (if days < lead_time + delay)
    holding_cost = sim_df['current_stock'] * 2.0 * cost_multiplier
    lead_time = sim_df.get('supplier_lead_time', pd.Series([7]*len(sim_df)))
    
    # Factory shutdown (capacity=0) means lead time goes to infinity
    eff_lead = lead_time + sim_df['sim_delay_days']
    if supplier_capacity == 0:
        eff_lead = 999 

    stockout_cost = np.where(
        sim_df['sim_days_until_stockout'] < eff_lead,
        sim_df['sim_demand'] * 5.0 * cost_multiplier,
        0
    )
    
    sim_df['sim_financial_impact'] = holding_cost + stockout_cost

    return sim_df

def run_monte_carlo(df, delay_days=0, demand_spike=0, supplier_capacity=100, cost_multiplier=1.0, iterations=1000):
    if df.empty:
        return []

    results = []
    base_demand = df['predicted_demand'].sum() if 'predicted_demand' in df.columns else 1000
    base_stock = df['current_stock'].sum() if 'current_stock' in df.columns else 5000

    for i in range(iterations):
        # Add random noise around the scenario parameters
        r_delay = max(0, np.random.normal(delay_days, max(1, delay_days * 0.2)))
        r_demand_spike = np.random.normal(demand_spike, max(5, abs(demand_spike) * 0.2))
        r_cost = max(0.5, np.random.normal(cost_multiplier, 0.1))
        
        sim_demand = base_demand * (1 + r_demand_spike / 100.0)
        sim_days = base_stock / sim_demand if sim_demand > 0 else 999
        
        eff_lead = 7 + r_delay if supplier_capacity > 0 else 999
        
        impact = base_stock * 2.0 * r_cost
        if sim_days < eff_lead:
            impact += sim_demand * 5.0 * r_cost
            
        results.append(impact)

    return results
