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

# =====================================================================
# SimPy Discrete-Event Simulation for Warehouse Operations
# =====================================================================
import simpy
import random

class WarehouseSimulation:
    def __init__(self, env, num_docks, num_workers, capacity):
        self.env = env
        self.docks = simpy.Resource(env, num_docks)
        self.workers = simpy.Resource(env, num_workers)
        self.capacity = simpy.Container(env, init=capacity, capacity=capacity)
        self.processed_shipments = 0
        self.delayed_shipments = 0
        self.backlog_time = 0.0

    def process_shipment(self, name, size, processing_time):
        arrival_time = self.env.now
        
        # Request a dock
        with self.docks.request() as dock_req:
            yield dock_req
            
            # Request workers to unload
            with self.workers.request() as worker_req:
                yield worker_req
                
                # Check if warehouse has capacity
                if self.capacity.level - size < 0:
                    self.delayed_shipments += 1
                    # Wait for space (simplified, just dropping or logging delay here)
                    wait_start = self.env.now
                    yield self.env.timeout(2.0)  # wait 2 hours for space
                    self.backlog_time += (self.env.now - wait_start)
                else:
                    # Put items in warehouse
                    yield self.capacity.get(size)
                    
                # Unloading time
                yield self.env.timeout(processing_time)
                
        finish_time = self.env.now
        self.processed_shipments += 1
        
        # If it took more than 4 hours, consider it delayed
        if (finish_time - arrival_time) > 4.0:
            self.delayed_shipments += 1
            self.backlog_time += (finish_time - arrival_time - 4.0)

def shipment_generator(env, warehouse, shipment_rate, avg_size):
    i = 0
    while True:
        yield env.timeout(random.expovariate(1.0 / shipment_rate))
        i += 1
        size = int(random.normalvariate(avg_size, avg_size * 0.2))
        processing_time = random.uniform(1.0, 3.0)
        env.process(warehouse.process_shipment(f"Shipment {i}", size, processing_time))

def run_agent_based_simulation(days=30, docks=3, workers=10, capacity=10000, shipment_rate=2.0, avg_size=500):
    """
    Runs a discrete-event simulation of a warehouse using SimPy.
    """
    env = simpy.Environment()
    warehouse = WarehouseSimulation(env, num_docks=docks, num_workers=workers, capacity=capacity)
    
    # Start the shipment generator
    env.process(shipment_generator(env, warehouse, shipment_rate, avg_size))
    
    # Run the simulation
    env.run(until=days * 24)  # run in hours
    
    return {
        "days_simulated": days,
        "processed_shipments": warehouse.processed_shipments,
        "delayed_shipments": warehouse.delayed_shipments,
        "total_backlog_hours": round(warehouse.backlog_time, 2),
        "delay_rate": round(warehouse.delayed_shipments / max(1, warehouse.processed_shipments) * 100, 2)
    }

