#!/usr/bin/env python3
"""
Seed sample data from generated CSV files into the Phase-1 SQLite DB.

Usage: python scripts/seed_sample_data.py --dir dataset/synthetic
This will create `products`, `suppliers`, and a small set of sales-derived
`Forecast` rows to help populate the dashboard.
"""
import os
import sys
import csv
from datetime import datetime

# Ensure project root on path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.database import SessionLocal, init_db
from backend.models import Product, Supplier, Forecast, User


def seed(dirpath: str):
    init_db()
    session = SessionLocal()
    try:
        # Seed suppliers
        sup_file = os.path.join(dirpath, "suppliers.csv")
        if os.path.exists(sup_file):
            with open(sup_file, newline="", encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                for r in reader:
                    s = Supplier(
                        supplier_id=r["supplier_id"],
                        supplier_name=r["supplier_name"],
                        lead_time_days=float(r.get("lead_time_days") or 7),
                        reliability_score=float(r.get("reliability_score") or 90.0),
                        delay_rate=float(r.get("delay_rate") or 0.0),
                        status=r.get("status", "ACTIVE")
                    )
                    session.add(s)

        # Seed products
        prod_file = os.path.join(dirpath, "products.csv")
        if os.path.exists(prod_file):
            with open(prod_file, newline="", encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                for r in reader:
                    p = Product(
                        product_id=r["product_id"],
                        product_name=r["product_name"],
                        current_stock=float(r.get("current_stock") or 0),
                        safety_stock=float(r.get("safety_stock") or 10),
                        reorder_point=float(r.get("reorder_point") or 50),
                        warehouse_id=r.get("warehouse_id") or "W1",
                        last_updated=datetime.utcnow()
                    )
                    session.add(p)

        session.commit()

        # Create a lightweight forecast per product (placeholder)
        user = session.query(User).first()
        if not user:
            user = User(username="system", email="system@example.com", password_hash="", is_active=False)
            session.add(user)
            session.commit()

        products = session.query(Product).limit(100).all()
        for p in products:
            f = Forecast(
                user_id=user.id,
                product_id=p.id,
                predicted_demand=round(max(1.0, p.current_stock * 0.1), 2),
                avg_daily_sales=round(max(0.1, p.current_stock * 0.02), 2),
                demand_spike=False,
                days_until_stockout=round(p.current_stock / max(1.0, p.current_stock * 0.02), 2),
                confidence_score=0.8,
                model_version="v1.0"
            )
            session.add(f)

        session.commit()
        print("Seeding complete.")
    finally:
        session.close()


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", default=os.path.join("dataset", "synthetic"))
    args = parser.parse_args()
    seed(args.dir)


if __name__ == "__main__":
    main()
