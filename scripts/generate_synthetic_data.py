#!/usr/bin/env python3
"""
Generate synthetic supply-chain CSV datasets (products, suppliers, sales).

Usage: python scripts/generate_synthetic_data.py [--products N] [--days D]
Files are written to the `DATASET_DIR` configured in `config.py` (default: dataset/).
"""
import os
import sys
import csv
import argparse
import random
from faker import Faker
from datetime import date, timedelta

# Ensure project root is on sys.path when executed from scripts folder
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import DATASET_DIR


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def generate_suppliers(path, count=10):
    fname = os.path.join(path, "suppliers.csv")
    fake = Faker()
    statuses = ["ACTIVE", "INACTIVE", "AT_RISK"]
    with open(fname, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["supplier_id", "supplier_name", "lead_time_days", "reliability_score", "delay_rate", "status"])
        for i in range(1, count + 1):
            sid = f"SUP{i:04d}"
            writer.writerow([
                sid,
                fake.company(),
                random.randint(2, 30),
                round(random.uniform(70.0, 99.9), 2),
                round(random.uniform(0.0, 0.3), 3),
                random.choice(statuses)
            ])
    return fname


def generate_products(path, count=100):
    fname = os.path.join(path, "products.csv")
    fake = Faker()
    with open(fname, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["product_id", "product_name", "current_stock", "safety_stock", "reorder_point", "warehouse_id"])
        for i in range(1, count + 1):
            pid = f"P{i:06d}"
            writer.writerow([
                pid,
                fake.catch_phrase(),
                random.randint(0, 5000),
                random.randint(10, 200),
                random.randint(50, 1000),
                f"W{random.randint(1,5)}"
            ])
    return fname


def generate_sales(path, products_file, days=90):
    fname = os.path.join(path, "sales.csv")
    product_ids = []
    with open(products_file, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for r in reader:
            product_ids.append(r["product_id"])

    start = date.today() - timedelta(days=days)
    channels = ["online", "retail", "distributor"]
    with open(fname, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["date", "product_id", "quantity", "sales_channel"])
        for d in range(days):
            day = start + timedelta(days=d)
            for _ in range(random.randint(20, 200)):
                pid = random.choice(product_ids)
                qty = max(1, int(random.gauss(20, 10)))
                writer.writerow([day.isoformat(), pid, qty, random.choice(channels)])
    return fname


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--products", type=int, default=200)
    parser.add_argument("--suppliers", type=int, default=20)
    parser.add_argument("--days", type=int, default=90)
    args = parser.parse_args()

    out_dir = os.path.join(DATASET_DIR, "synthetic")
    ensure_dir(out_dir)
    print("Generating suppliers...")
    suppliers = generate_suppliers(out_dir, count=args.suppliers)
    print("Generating products...")
    products = generate_products(out_dir, count=args.products)
    print("Generating sales...")
    sales = generate_sales(out_dir, products, days=args.days)

    print("Generated:")
    print(f" - {suppliers}")
    print(f" - {products}")
    print(f" - {sales}")


if __name__ == "__main__":
    main()
