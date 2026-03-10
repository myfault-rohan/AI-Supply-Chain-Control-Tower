"""
Supply Chain Data Generator
Generates realistic manufacturing supply chain datasets
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

# Set random seed for reproducibility
np.random.seed(42)
random.seed(42)

# Configuration
NUM_PRODUCTS = 100
NUM_WAREHOUSES = 5
NUM_SUPPLIERS = 20
NUM_DAYS = 365
START_DATE = datetime(2024, 1, 1)

# Product categories and names
CATEGORIES = {
    'Electronics': ['Laptop', 'Smartphone', 'Tablet', 'Monitor', 'Keyboard', 'Mouse', 'Headphones', 'Webcam', 'Router', 'Hard Drive'],
    'Machinery': ['Motor', 'Pump', 'Conveyor Belt', 'Generator', 'Transformer', 'Compressor', 'Hydraulic Press', 'CNC Machine', 'Lathe', 'Welding Equipment'],
    'Raw Materials': ['Steel Sheet', 'Aluminum Rod', 'Copper Wire', 'Plastic Pellet', 'Rubber Sheet', 'Glass Panel', 'Wood Plank', 'Fabric Roll', 'Chemical Solvent', 'Adhesive'],
    'Components': ['Bearing', 'Gear', 'Spring', 'Bolt', 'Nut', 'Washer', 'Seal', 'Belt', 'Chain', 'Bushing'],
    'Office Supplies': ['Paper', 'Pen', 'Notebook', 'Folder', 'Stapler', 'Tape', 'Scissors', 'Marker', 'Clipboard', 'Calculator']
}

REGIONS = ['North', 'South', 'East', 'West', 'Central']

WAREHOUSE_LOCATIONS = [
    'Chicago, IL',
    'Dallas, TX',
    'Los Angeles, CA',
    'New York, NY',
    'Atlanta, GA'
]

SUPPLIER_NAMES = [
    'Global Tech Supplies', 'Premier Materials Inc', 'Industrial Solutions Ltd',
    'Quality Parts Co', 'Pacific Supply Chain', 'Atlantic Manufacturing',
    'Midwest Components', 'Southern Industries', 'Northern Resources',
    'Eastern Trading Co', 'Western Distribution', 'United Suppliers',
    'Precision Parts Inc', 'Advanced Materials Corp', 'Reliable Sources LLC',
    'Strategic Partners Inc', 'Elite Manufacturing', 'Procurement Experts',
    'Integrated Supply Co', 'Total Solutions Ltd'
]

SHIPMENT_STATUSES = ['Pending', 'In Transit', 'Delivered', 'Delayed', 'Cancelled']


def generate_products():
    """Generate products dataset"""
    products = []
    product_id = 1
    
    for category, names in CATEGORIES.items():
        for name in names:
            # Generate variations for each product type
            for variant in range(NUM_PRODUCTS // len(CATEGORIES)):
                products.append({
                    'product_id': f'PROD-{product_id:04d}',
                    'product_name': f'{name} {chr(65 + variant)}',
                    'category': category,
                    'unit_price': round(np.random.uniform(10, 5000), 2)
                })
                product_id += 1
                if product_id > NUM_PRODUCTS:
                    break
            if product_id > NUM_PRODUCTS:
                break
        if product_id > NUM_PRODUCTS:
            break
    
    return pd.DataFrame(products[:NUM_PRODUCTS])


def generate_warehouses():
    """Generate warehouses dataset"""
    warehouses = []
    
    for i in range(NUM_WAREHOUSES):
        warehouses.append({
            'warehouse_id': f'WH-{i+1:02d}',
            'warehouse_location': WAREHOUSE_LOCATIONS[i],
            'capacity': random.randint(50000, 200000)
        })
    
    return pd.DataFrame(warehouses)


def generate_suppliers():
    """Generate suppliers dataset"""
    suppliers = []
    
    for i in range(NUM_SUPPLIERS):
        suppliers.append({
            'supplier_id': f'SUP-{i+1:03d}',
            'supplier_name': SUPPLIER_NAMES[i],
            'lead_time_days': random.randint(3, 30),
            'reliability_score': round(random.uniform(0.7, 0.99), 2)
        })
    
    return pd.DataFrame(suppliers)


def generate_inventory(products_df, warehouses_df):
    """Generate inventory dataset with relationships to products and warehouses"""
    inventory = []
    
    # Each product is stored in 1-3 warehouses
    for _, product in products_df.iterrows():
        num_warehouses = random.randint(1, 3)
        selected_warehouses = warehouses_df.sample(n=num_warehouses)
        
        for _, warehouse in selected_warehouses.iterrows():
            capacity_factor = random.uniform(0.3, 0.8)
            capacity = warehouse['capacity']
            current_stock = int(capacity * capacity_factor)
            safety_stock = int(current_stock * random.uniform(0.1, 0.3))
            reorder_point = int(safety_stock * random.uniform(1.5, 2.5))
            
            inventory.append({
                'product_id': product['product_id'],
                'warehouse_id': warehouse['warehouse_id'],
                'current_stock': current_stock,
                'safety_stock': safety_stock,
                'reorder_point': reorder_point
            })
    
    return pd.DataFrame(inventory)


def generate_sales(products_df):
    """Generate 365 days of sales data"""
    sales = []
    
    for day_offset in range(NUM_DAYS):
        current_date = START_DATE + timedelta(days=day_offset)
        
        # Each day, 60-80% of products have sales
        num_products_with_sales = int(NUM_PRODUCTS * random.uniform(0.6, 0.8))
        sampled_products = products_df.sample(n=num_products_with_sales)
        
        for _, product in sampled_products.iterrows():
            # Weekend sales are typically lower
            day_of_week = current_date.weekday()
            base_demand = random.randint(1, 50)
            if day_of_week >= 5:  # Saturday, Sunday
                base_demand = int(base_demand * 0.6)
            
            # Add some seasonality
            month = current_date.month
            if month in [11, 12]:  # Holiday season
                base_demand = int(base_demand * 1.3)
            elif month in [1, 2]:  # Post-holiday slump
                base_demand = int(base_demand * 0.7)
            
            sales.append({
                'product_id': product['product_id'],
                'date': current_date.strftime('%Y-%m-%d'),
                'daily_sales': base_demand,
                'region': random.choice(REGIONS)
            })
    
    return pd.DataFrame(sales)


def generate_shipments(suppliers_df, products_df):
    """Generate shipments dataset with relationships to suppliers and products"""
    shipments = []
    shipment_id = 1
    
    # Generate shipments over the year (roughly 2-5 shipments per day)
    num_shipments = NUM_DAYS * random.randint(2, 5)
    
    for _ in range(num_shipments):
        # Random date within the year
        days_offset = random.randint(0, NUM_DAYS - 1)
        shipment_date = START_DATE + timedelta(days=days_offset)
        
        supplier = suppliers_df.sample(n=1).iloc[0]
        product = products_df.sample(n=1).iloc[0]
        
        # Expected delivery based on lead time
        lead_time = int(supplier['lead_time_days'])
        expected_delivery = shipment_date + timedelta(days=lead_time)
        
        # Actual delivery with some variation
        reliability = supplier['reliability_score']
        if random.random() < reliability:
            # On time or early
            actual_delivery = expected_delivery + timedelta(days=random.randint(-2, 2))
            status = 'Delivered'
        else:
            # Delayed
            actual_delivery = expected_delivery + timedelta(days=random.randint(3, 10))
            status = 'Delayed'
        
        # Some shipments might still be pending
        if days_offset > NUM_DAYS - 30:  # Last month
            if random.random() < 0.3:
                actual_delivery = None
                status = random.choice(['Pending', 'In Transit'])
        
        shipments.append({
            'shipment_id': f'SHIP-{shipment_id:06d}',
            'supplier_id': supplier['supplier_id'],
            'product_id': product['product_id'],
            'shipment_date': shipment_date.strftime('%Y-%m-%d'),
            'expected_delivery': expected_delivery.strftime('%Y-%m-%d'),
            'actual_delivery': actual_delivery.strftime('%Y-%m-%d') if actual_delivery else None,
            'status': status
        })
        
        shipment_id += 1
    
    return pd.DataFrame(shipments)


def main():
    """Main function to generate and save all datasets"""
    print("Generating supply chain datasets...")
    
    # Generate all datasets
    print("Generating products...")
    products_df = generate_products()
    
    print("Generating warehouses...")
    warehouses_df = generate_warehouses()
    
    print("Generating suppliers...")
    suppliers_df = generate_suppliers()
    
    print("Generating inventory...")
    inventory_df = generate_inventory(products_df, warehouses_df)
    
    print("Generating sales (365 days)...")
    sales_df = generate_sales(products_df)
    
    print("Generating shipments...")
    shipments_df = generate_shipments(suppliers_df, products_df)
    
    # Save to dataset folder
    output_dir = 'dataset/'
    
    print(f"Saving datasets to {output_dir}...")
    products_df.to_csv(f'{output_dir}products.csv', index=False)
    warehouses_df.to_csv(f'{output_dir}warehouses.csv', index=False)
    suppliers_df.to_csv(f'{output_dir}suppliers.csv', index=False)
    inventory_df.to_csv(f'{output_dir}inventory.csv', index=False)
    sales_df.to_csv(f'{output_dir}sales.csv', index=False)
    shipments_df.to_csv(f'{output_dir}shipments.csv', index=False)
    
    # Print summary
    print("\n" + "="*50)
    print("DATASET SUMMARY")
    print("="*50)
    print(f"Products:       {len(products_df):,} records")
    print(f"Warehouses:     {len(warehouses_df):,} records")
    print(f"Suppliers:      {len(suppliers_df):,} records")
    print(f"Inventory:      {len(inventory_df):,} records")
    print(f"Sales:          {len(sales_df):,} records")
    print(f"Shipments:       {len(shipments_df):,} records")
    print("="*50)
    print("Data generation complete!")


if __name__ == "__main__":
    main()

