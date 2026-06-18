"""
etl/olist_loader.py
====================
Loads, validates, and joins the 9 Olist CSV tables.

Responsibilities:
  - Load each CSV with correct dtypes and parse timestamps
  - Validate shapes, required columns, and referential integrity
  - Expose a single load_olist() function that returns a dict of DataFrames
  - Expose a build_master() function that returns the fully joined master table
    (one row per order-item) used by all downstream feature engineering

Expected files in data/raw/:
  olist_orders_dataset.csv
  olist_order_items_dataset.csv
  olist_order_reviews_dataset.csv
  olist_sellers_dataset.csv
  olist_products_dataset.csv
  olist_customers_dataset.csv
  olist_order_payments_dataset.csv
  olist_geolocation_dataset.csv
  product_category_name_translation.csv
"""

import os
import pandas as pd
import numpy as np

# â”€â”€ Path configuration â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW_DIR = os.path.join(ROOT, "data", "raw")
PROCESSED_DIR = os.path.join(ROOT, "data", "processed")
os.makedirs(PROCESSED_DIR, exist_ok=True)

# â”€â”€ Expected schema: (required columns, parse_dates list) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
SCHEMAS = {
    "orders": {
        "file": "olist_orders_dataset.csv",
        "required": [
            "order_id", "customer_id", "order_status",
            "order_purchase_timestamp", "order_approved_at",
            "order_delivered_carrier_date", "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ],
        "parse_dates": [
            "order_purchase_timestamp", "order_approved_at",
            "order_delivered_carrier_date", "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ],
    },
    "items": {
        "file": "olist_order_items_dataset.csv",
        "required": [
            "order_id", "order_item_id", "product_id",
            "seller_id", "price", "freight_value",
        ],
        "parse_dates": ["shipping_limit_date"],
    },
    "reviews": {
        "file": "olist_order_reviews_dataset.csv",
        "required": [
            "review_id", "order_id", "review_score",
        ],
        "parse_dates": ["review_creation_date", "review_answer_timestamp"],
    },
    "sellers": {
        "file": "olist_sellers_dataset.csv",
        "required": ["seller_id", "seller_zip_code_prefix", "seller_city", "seller_state"],
        "parse_dates": [],
    },
    "products": {
        "file": "olist_products_dataset.csv",
        "required": ["product_id", "product_category_name"],
        "parse_dates": [],
    },
    "customers": {
        "file": "olist_customers_dataset.csv",
        "required": ["customer_id", "customer_zip_code_prefix", "customer_state"],
        "parse_dates": [],
    },
    "payments": {
        "file": "olist_order_payments_dataset.csv",
        "required": ["order_id", "payment_type", "payment_value"],
        "parse_dates": [],
    },
    "geolocation": {
        "file": "olist_geolocation_dataset.csv",
        "required": [
            "geolocation_zip_code_prefix", "geolocation_lat",
            "geolocation_lng", "geolocation_state",
        ],
        "parse_dates": [],
    },
    "category_translation": {
        "file": "product_category_name_translation.csv",
        "required": ["product_category_name", "product_category_name_english"],
        "parse_dates": [],
    },
}


def load_olist(raw_dir: str = RAW_DIR, verbose: bool = True) -> dict:
    """
    Load all 9 Olist tables from raw_dir.
    Returns a dict keyed by table name (e.g. 'orders', 'items', 'reviews', ...).
    Raises FileNotFoundError if any expected file is missing.
    Prints a validation summary when verbose=True.
    """
    tables = {}
    errors = []

    for name, schema in SCHEMAS.items():
        path = os.path.join(raw_dir, schema["file"])

        if not os.path.exists(path):
            errors.append(f"MISSING FILE: {schema['file']}")
            continue

        try:
            df = pd.read_csv(
                path,
                parse_dates=schema["parse_dates"] if schema["parse_dates"] else False,
                low_memory=False,
            )

            # Validate required columns
            missing_cols = [c for c in schema["required"] if c not in df.columns]
            if missing_cols:
                errors.append(f"{name}: missing columns {missing_cols}")
                continue

            tables[name] = df

            if verbose:
                null_pct = df.isnull().mean().mean() * 100
                print(
                    f"  âœ… {name:<22} {len(df):>7,} rows Ã— {len(df.columns):>2} cols"
                    f"  |  null%={null_pct:.1f}%"
                    f"  |  {schema['file']}"
                )
        except Exception as e:
            errors.append(f"{name}: load error â€” {e}")

    if errors:
        print("\nâŒ ERRORS:")
        for e in errors:
            print(f"  {e}")
        raise RuntimeError(f"Olist loader failed with {len(errors)} error(s). See above.")

    if verbose:
        print(f"\n  Loaded {len(tables)}/9 tables successfully.")

    return tables


def build_master(tables: dict, verbose: bool = True) -> pd.DataFrame:
    """
    Build a single master DataFrame â€” one row per order-item â€” by joining:
      orders â†’ items â†’ sellers â†’ reviews (first review per order) â†’ products â†’ category_translation

    This is the base table for all feature engineering.

    Key computed columns added here:
      dispatch_days       : days from order_approved_at to order_delivered_carrier_date
      delivery_days       : days from order_approved_at to order_delivered_customer_date
      estimated_days      : days from order_approved_at to order_estimated_delivery_date
      delivery_delay_days : actual delivery - estimated delivery (positive = late)
      is_late             : bool, delivery_delay_days > 0
      on_time             : bool, not is_late (and delivered)
      purchase_month      : year-month period for time-series grouping
    """
    orders = tables["orders"].copy()
    items = tables["items"].copy()
    sellers = tables["sellers"].copy()
    reviews = tables["reviews"].copy()
    products = tables["products"].copy()
    cat_trans = tables["category_translation"].copy()

    # â”€â”€ Join items â†’ orders â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    master = items.merge(orders, on="order_id", how="left")

    # â”€â”€ Join sellers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    master = master.merge(sellers, on="seller_id", how="left")

    # â”€â”€ Join reviews â€” take FIRST review per order (some orders have multiple) â”€
    # Keep only the columns we need; deduplicate on order_id
    reviews_clean = (
        reviews[["order_id", "review_score", "review_creation_date"]]
        .sort_values("review_creation_date")
        .drop_duplicates(subset="order_id", keep="first")
    )
    master = master.merge(reviews_clean, on="order_id", how="left")

    # â”€â”€ Join product category â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    products_with_cat = products[["product_id", "product_category_name"]].merge(
        cat_trans, on="product_category_name", how="left"
    )
    master = master.merge(products_with_cat, on="product_id", how="left")

    # â”€â”€ Derived time columns â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _days(end_col, start_col):
        return (master[end_col] - master[start_col]).dt.total_seconds() / 86400

    master["dispatch_days"] = _days("order_delivered_carrier_date", "order_approved_at")
    master["delivery_days"] = _days("order_delivered_customer_date", "order_approved_at")
    master["estimated_days"] = _days("order_estimated_delivery_date", "order_approved_at")
    master["delivery_delay_days"] = _days("order_delivered_customer_date", "order_estimated_delivery_date")

    # Only delivered orders have meaningful delay signal
    delivered = master["order_status"] == "delivered"
    master["is_late"] = delivered & (master["delivery_delay_days"] > 0)
    master["on_time"] = delivered & (master["delivery_delay_days"] <= 0)

    # â”€â”€ Time grouping â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    master["purchase_month"] = master["order_purchase_timestamp"].dt.to_period("M")
    master["purchase_week"] = master["order_purchase_timestamp"].dt.to_period("W")
    master["purchase_year"] = master["order_purchase_timestamp"].dt.year

    if verbose:
        print(f"\n  Master table: {len(master):,} rows Ã— {len(master.columns)} columns")

        delivered_mask = master["order_status"] == "delivered"
        print(f"  Delivered orders:   {delivered_mask.sum():,} ({delivered_mask.mean()*100:.1f}%)")

        late_mask = master["is_late"]
        print(f"  Late deliveries:    {late_mask.sum():,} ({late_mask.mean()*100:.1f}%)")

        sellers_count = master["seller_id"].nunique()
        print(f"  Unique sellers:     {sellers_count:,}")

        date_min = master["order_purchase_timestamp"].min()
        date_max = master["order_purchase_timestamp"].max()
        print(f"  Date range:         {date_min.date()} â†’ {date_max.date()}")

        dispatch_median = master.loc[master["dispatch_days"] > 0, "dispatch_days"].median()
        dispatch_p95 = master.loc[master["dispatch_days"] > 0, "dispatch_days"].quantile(0.95)
        print(f"  Dispatch days:      median={dispatch_median:.1f}d, p95={dispatch_p95:.1f}d")

        review_mean = master["review_score"].mean()
        print(f"  Mean review score:  {review_mean:.2f} / 5.0")

    return master


if __name__ == "__main__":
    print("=" * 65)
    print("  Olist Loader â€” Validation Run")
    print("=" * 65)
    tables = load_olist(verbose=True)
    print()
    master = build_master(tables, verbose=True)
    print()

    # Save master for downstream use
    out_path = os.path.join(PROCESSED_DIR, "master.parquet")
    master.to_parquet(out_path, index=False)
    print(f"\n  Saved master table â†’ {out_path}")
    print("=" * 65)

