#!/usr/bin/env python3
"""
Seed sample data from generated CSV files into the Phase-1 SQLite DB.

Usage: python scripts/seed_sample_data.py --dir dataset/synthetic

Uses merge (upsert) logic so it is safe to run multiple times — existing
records are updated in-place rather than raising IntegrityError.
"""
import os
import sys
import csv
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.database import SessionLocal, init_db
from backend.models import Product, Supplier, Forecast, User


def seed(dirpath: str):
    init_db()
    session = SessionLocal()
    try:
        # ── Seed Suppliers (upsert) ───────────────────────────────────────────
        sup_file = os.path.join(dirpath, "suppliers.csv")
        if os.path.exists(sup_file):
            with open(sup_file, newline="", encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                for r in reader:
                    existing = session.query(Supplier).filter_by(
                        supplier_id=r["supplier_id"]
                    ).first()
                    if existing:
                        # Update existing record
                        existing.supplier_name   = r["supplier_name"]
                        existing.lead_time_days  = float(r.get("lead_time_days") or 7)
                        existing.reliability_score = float(r.get("reliability_score") or 90.0)
                        existing.delay_rate      = float(r.get("delay_rate") or 0.0)
                        existing.status          = r.get("status", "ACTIVE")
                    else:
                        session.add(Supplier(
                            supplier_id      = r["supplier_id"],
                            supplier_name    = r["supplier_name"],
                            lead_time_days   = float(r.get("lead_time_days") or 7),
                            reliability_score= float(r.get("reliability_score") or 90.0),
                            delay_rate       = float(r.get("delay_rate") or 0.0),
                            status           = r.get("status", "ACTIVE"),
                        ))
            session.commit()
            print(f"  Suppliers seeded/updated from {sup_file}")

        # ── Seed Products (upsert) ────────────────────────────────────────────
        prod_file = os.path.join(dirpath, "products.csv")
        if os.path.exists(prod_file):
            with open(prod_file, newline="", encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                for r in reader:
                    existing = session.query(Product).filter_by(
                        product_id=r["product_id"]
                    ).first()
                    if existing:
                        existing.product_name  = r["product_name"]
                        existing.current_stock = float(r.get("current_stock") or 0)
                        existing.safety_stock  = float(r.get("safety_stock") or 10)
                        existing.reorder_point = float(r.get("reorder_point") or 50)
                        existing.warehouse_id  = r.get("warehouse_id") or "W1"
                        existing.last_updated  = datetime.now()
                    else:
                        session.add(Product(
                            product_id   = r["product_id"],
                            product_name = r["product_name"],
                            current_stock= float(r.get("current_stock") or 0),
                            safety_stock = float(r.get("safety_stock") or 10),
                            reorder_point= float(r.get("reorder_point") or 50),
                            warehouse_id = r.get("warehouse_id") or "W1",
                            last_updated = datetime.now(),
                        ))
            session.commit()
            print(f"  Products seeded/updated from {prod_file}")

        # ── Seed Forecasts (replace all) ──────────────────────────────────────
        # Delete old forecasts and recreate — they're cheap to regenerate
        session.query(Forecast).delete()
        session.commit()

        user = session.query(User).first()
        if not user:
            user = User(
                username="system",
                email="system@example.com",
                password_hash="",
                is_active=False
            )
            session.add(user)
            session.commit()

        products = session.query(Product).limit(100).all()
        for p in products:
            session.add(Forecast(
                user_id         = user.id,
                product_id      = p.id,
                predicted_demand= round(max(1.0, p.current_stock * 0.1), 2),
                avg_daily_sales = round(max(0.1, p.current_stock * 0.02), 2),
                demand_spike    = False,
                days_until_stockout = round(p.current_stock / max(1.0, p.current_stock * 0.02), 2),
                confidence_score= 0.8,
                model_version   = "v1.0",
            ))

        session.commit()
        print("  Seeding complete.")

    except Exception as e:
        session.rollback()
        print(f"  ERROR during seeding: {e}")
        raise
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
