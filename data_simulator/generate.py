#!/usr/bin/env python3
"""
Synthetic Supply Chain Data Generator
======================================
Generates realistic multi-year supply chain data with:
- Seasonal demand patterns (Christmas, summer)
- Random supplier disruption events
- Multiple product categories with different demand profiles
- Correlated inventory & sales data

Output: data/raw/*.csv
"""

import numpy as np
import pandas as pd
import os
from datetime import datetime, timedelta
import random

random.seed(42)
np.random.seed(42)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(ROOT, "data", "raw")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Config ──────────────────────────────────────────────────────────────────
N_PRODUCTS    = 100
N_WAREHOUSES  = 5
N_SUPPLIERS   = 20
N_DAYS        = 3 * 365   # 3 years (Jan 2022 – Dec 2024)
START_DATE    = datetime(2022, 1, 1)

CATEGORIES = {
    "Electronics":   {"base_demand": 25, "volatility": 0.35, "margin": 0.40},
    "Clothing":      {"base_demand": 40, "volatility": 0.50, "margin": 0.55},
    "Food":          {"base_demand": 80, "volatility": 0.20, "margin": 0.25},
    "Industrial":    {"base_demand": 15, "volatility": 0.15, "margin": 0.30},
    "Pharmaceuticals":{"base_demand": 20, "volatility": 0.10, "margin": 0.60},
}


def seasonal_factor(date):
    """Return a demand multiplier for date-based seasonality."""
    doy = date.timetuple().tm_yday
    month = date.month
    # Christmas spike (Nov-Dec)
    if month in (11, 12):
        return 1.0 + 0.6 * np.sin(np.pi * (doy - 300) / 60)
    # Summer dip (June-Aug)
    if month in (6, 7, 8):
        return 0.80
    # Spring/Back-to-school bump
    if month in (3, 4, 9):
        return 1.15
    return 1.0


def generate_products():
    rows = []
    cat_list = list(CATEGORIES.keys())
    for i in range(1, N_PRODUCTS + 1):
        cat = cat_list[(i - 1) % len(cat_list)]
        cfg = CATEGORIES[cat]
        unit_cost = round(random.uniform(5, 500), 2)
        rows.append({
            "product_id":    f"PROD-{i:04d}",
            "product_name":  f"{cat} Product {i:03d}",
            "category":      cat,
            "unit_cost":     unit_cost,
            "unit_price":    round(unit_cost * (1 + cfg["margin"]), 2),
            "base_demand":   cfg["base_demand"],
            "demand_volatility": cfg["volatility"],
            "warehouse_id":  f"WH-{((i-1) % N_WAREHOUSES) + 1:02d}",
            "supplier_id":   f"SUP-{((i-1) % N_SUPPLIERS) + 1:02d}",
            "lead_time_days": random.randint(3, 30),
            "safety_stock":  random.randint(20, 100),
            "reorder_point": random.randint(50, 200),
            "holding_cost_rate": round(random.uniform(0.15, 0.30), 2),
            "ordering_cost":     round(random.uniform(50, 500), 2),
        })
    return pd.DataFrame(rows)


def generate_warehouses():
    rows = []
    for i in range(1, N_WAREHOUSES + 1):
        rows.append({
            "warehouse_id":   f"WH-{i:02d}",
            "warehouse_name": f"Distribution Center {i}",
            "location":       random.choice(["Mumbai", "Delhi", "Chennai", "Kolkata", "Bangalore"]),
            "capacity":       random.randint(5000, 20000),
            "fixed_cost_monthly": random.randint(50000, 200000),
        })
    return pd.DataFrame(rows)


def generate_suppliers():
    rows = []
    for i in range(1, N_SUPPLIERS + 1):
        base_reliability = random.uniform(0.70, 0.99)
        rows.append({
            "supplier_id":        f"SUP-{i:02d}",
            "supplier_name":      f"Supplier {i} Ltd",
            "country":            random.choice(["India", "China", "USA", "Germany", "Japan", "Vietnam"]),
            "reliability_score":  round(base_reliability * 100, 1),
            "avg_lead_time_days": random.randint(5, 45),
            "lead_time_std":      random.randint(1, 10),
            "defect_rate":        round((1 - base_reliability) * 0.5, 4),
            "on_time_delivery_rate": round(base_reliability * 100, 1),
            "payment_terms_days": random.choice([15, 30, 45, 60, 90]),
            "risk_category":      "HIGH" if base_reliability < 0.80 else ("MEDIUM" if base_reliability < 0.92 else "LOW"),
        })
    return pd.DataFrame(rows)


def generate_daily_sales(products_df, suppliers_df):
    """Generate daily sales with seasonality, trends, and disruption events."""
    print("  Generating daily sales (this takes ~10s)...")
    dates = [START_DATE + timedelta(days=d) for d in range(N_DAYS)]

    # Generate random disruption events (e.g., supplier shutdowns, port strikes)
    disruptions = []
    for _ in range(15):
        start = random.randint(0, N_DAYS - 30)
        disruptions.append({
            "start": start,
            "end": start + random.randint(7, 45),
            "supplier_id": f"SUP-{random.randint(1, N_SUPPLIERS):02d}",
            "severity": random.uniform(0.3, 0.9),
        })

    rows = []
    for _, prod in products_df.iterrows():
        # Long-term trend (+15% over 3 years)
        trend = np.linspace(1.0, 1.15, N_DAYS)

        for d_idx, date in enumerate(dates):
            base = prod["base_demand"]
            season = seasonal_factor(date)
            vol = prod["demand_volatility"]
            noise = np.random.lognormal(0, vol)

            # Check for disruptions affecting this supplier
            disruption_factor = 1.0
            for dis in disruptions:
                if (dis["supplier_id"] == prod["supplier_id"] and
                        dis["start"] <= d_idx <= dis["end"]):
                    disruption_factor = 1.0 - dis["severity"] * 0.5

            demand = max(0, base * season * trend[d_idx] * noise * disruption_factor)
            rows.append({
                "date":        date.strftime("%Y-%m-%d"),
                "product_id":  prod["product_id"],
                "category":    prod["category"],
                "warehouse_id": prod["warehouse_id"],
                "supplier_id": prod["supplier_id"],
                "daily_sales": round(demand, 2),
                "revenue":     round(demand * prod["unit_price"], 2),
                "is_disrupted": disruption_factor < 1.0,
            })

    return pd.DataFrame(rows)


def generate_inventory_snapshot(products_df, sales_df):
    """Create current inventory state from sales history."""
    last_30 = sales_df[sales_df["date"] >= sales_df["date"].max()[:7]].groupby("product_id")["daily_sales"].mean()
    rows = []
    for _, prod in products_df.iterrows():
        avg_daily = last_30.get(prod["product_id"], prod["base_demand"])
        current_stock = round(random.uniform(0.5, 4.0) * avg_daily * prod["lead_time_days"])
        rows.append({
            "product_id":       prod["product_id"],
            "product_name":     prod["product_name"],
            "category":         prod["category"],
            "warehouse_id":     prod["warehouse_id"],
            "supplier_id":      prod["supplier_id"],
            "current_stock":    current_stock,
            "safety_stock":     prod["safety_stock"],
            "reorder_point":    prod["reorder_point"],
            "lead_time_days":   prod["lead_time_days"],
            "avg_daily_sales":  round(avg_daily, 2),
            "days_of_stock":    round(current_stock / max(avg_daily, 0.1), 1),
            "unit_cost":        prod["unit_cost"],
            "holding_cost_rate": prod["holding_cost_rate"],
            "ordering_cost":    prod["ordering_cost"],
        })
    return pd.DataFrame(rows)


def generate_shipments(products_df, suppliers_df):
    rows = []
    dates = [START_DATE + timedelta(days=d) for d in range(N_DAYS)]
    shipment_id = 1
    for _, prod in products_df.iterrows():
        sup = suppliers_df[suppliers_df["supplier_id"] == prod["supplier_id"]].iloc[0]
        # ~1 shipment every 2 weeks per product
        for d_idx in range(0, N_DAYS, random.randint(10, 21)):
            order_date = dates[d_idx]
            lead = int(np.random.normal(sup["avg_lead_time_days"], sup["lead_time_std"]))
            lead = max(1, lead)
            actual_lead = lead + random.choices([0, random.randint(1,14)],
                                                 weights=[sup["on_time_delivery_rate"]/100,
                                                          1 - sup["on_time_delivery_rate"]/100])[0]
            qty = random.randint(50, 500)
            rows.append({
                "shipment_id":    f"SHP-{shipment_id:06d}",
                "product_id":     prod["product_id"],
                "supplier_id":    prod["supplier_id"],
                "warehouse_id":   prod["warehouse_id"],
                "order_date":     order_date.strftime("%Y-%m-%d"),
                "expected_date":  (order_date + timedelta(days=lead)).strftime("%Y-%m-%d"),
                "actual_date":    (order_date + timedelta(days=actual_lead)).strftime("%Y-%m-%d"),
                "quantity":       qty,
                "unit_cost":      prod["unit_cost"],
                "total_cost":     round(qty * prod["unit_cost"], 2),
                "delay_days":     max(0, actual_lead - lead),
                "on_time":        actual_lead <= lead,
                "defective_units": int(qty * sup["defect_rate"]),
            })
            shipment_id += 1
    return pd.DataFrame(rows)


def main():
    print("=" * 60)
    print("  Supply Chain Data Generator")
    print("=" * 60)

    print("\n[1/5] Generating products...")
    products = generate_products()
    products.to_csv(os.path.join(OUTPUT_DIR, "products.csv"), index=False)
    print(f"  ✅ {len(products)} products")

    print("[2/5] Generating warehouses...")
    warehouses = generate_warehouses()
    warehouses.to_csv(os.path.join(OUTPUT_DIR, "warehouses.csv"), index=False)
    print(f"  ✅ {len(warehouses)} warehouses")

    print("[3/5] Generating suppliers...")
    suppliers = generate_suppliers()
    suppliers.to_csv(os.path.join(OUTPUT_DIR, "suppliers.csv"), index=False)
    print(f"  ✅ {len(suppliers)} suppliers")

    print("[4/5] Generating daily sales (3 years × 100 products)...")
    sales = generate_daily_sales(products, suppliers)
    sales.to_csv(os.path.join(OUTPUT_DIR, "sales.csv"), index=False)
    print(f"  ✅ {len(sales):,} sales records")

    print("[5/5] Generating inventory & shipments...")
    inventory = generate_inventory_snapshot(products, sales)
    inventory.to_csv(os.path.join(OUTPUT_DIR, "inventory.csv"), index=False)

    shipments = generate_shipments(products, suppliers)
    shipments.to_csv(os.path.join(OUTPUT_DIR, "shipments.csv"), index=False)
    print(f"  ✅ {len(inventory)} inventory records, {len(shipments):,} shipments")

    print(f"\n{'='*60}")
    print(f"  Data saved to data/raw/")
    print(f"  Total sales records: {len(sales):,}")
    print(f"  Date range: {sales['date'].min()} → {sales['date'].max()}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
