#!/usr/bin/env python3
"""
Inventory Optimization — EOQ + Safety Stock
=============================================
Operations Research meets Data Science.
This model is RARE in DS portfolios — it directly quantifies
business value (cost savings) from optimized inventory decisions.

Methods:
  - Economic Order Quantity (EOQ): minimizes total ordering + holding costs
  - Safety Stock with service level targets (95% / 99%)
  - Reorder Point calculation using demand uncertainty
  - Total cost comparison: current vs optimized policy

Output: data/models/inventory_optimization.csv
"""

import pandas as pd
import numpy as np
import os, json
import warnings
warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DIR = os.path.join(ROOT, "data", "processed")
MODELS_DIR    = os.path.join(ROOT, "data", "models")
os.makedirs(MODELS_DIR, exist_ok=True)

# Service level → Z-score mapping
SERVICE_LEVELS = {
    0.90: 1.282,
    0.95: 1.645,
    0.99: 2.326,
}


def compute_eoq(annual_demand, ordering_cost, holding_cost_per_unit):
    """
    Classic Wilson EOQ formula:
      EOQ = sqrt(2 * D * S / H)
    where:
      D = annual demand
      S = ordering cost per order
      H = holding cost per unit per year
    """
    return np.sqrt(2 * annual_demand * ordering_cost / np.maximum(holding_cost_per_unit, 0.01))


def compute_safety_stock(demand_std_daily, lead_time_days, service_level=0.95):
    """
    Safety Stock = Z * σ_LT
    where σ_LT = σ_daily * sqrt(lead_time) (demand uncertainty during lead time)
    """
    z = SERVICE_LEVELS.get(service_level, 1.645)
    sigma_lt = demand_std_daily * np.sqrt(lead_time_days)
    return z * sigma_lt


def compute_reorder_point(avg_daily_demand, lead_time_days, safety_stock):
    """
    ROP = (avg_daily_demand × lead_time) + safety_stock
    """
    return avg_daily_demand * lead_time_days + safety_stock


def compute_total_annual_cost(avg_stock, order_qty, annual_demand,
                               ordering_cost, holding_cost_per_unit):
    """
    Total Cost = (Q/2 × H) + (D/Q × S)
    where Q = order quantity
    """
    holding  = (order_qty / 2) * holding_cost_per_unit
    ordering = (annual_demand / np.maximum(order_qty, 1)) * ordering_cost
    return holding + ordering


def load_data():
    inv = pd.read_csv(os.path.join(PROCESSED_DIR, "inventory_features.csv"))
    return inv


def main():
    print("=" * 60)
    print("  Inventory Optimization (EOQ + Safety Stock)")
    print("=" * 60)

    df = load_data()
    print(f"  Loaded {len(df)} products for optimization")

    # ── Derived inputs ────────────────────────────────────────────────────────
    df["annual_demand"]          = df["avg_daily_sales"] * 365
    df["holding_cost_per_unit"]  = df["unit_cost"] * df["holding_cost_rate"]
    df["demand_std_daily"]       = df["avg_daily_sales"] * 0.20   # approx 20% CV

    # ── EOQ Calculation ───────────────────────────────────────────────────────
    df["eoq"] = compute_eoq(
        df["annual_demand"],
        df["ordering_cost"],
        df["holding_cost_per_unit"]
    ).round(0)

    # ── Safety Stock at 95% and 99% service levels ────────────────────────────
    df["safety_stock_95"] = compute_safety_stock(
        df["demand_std_daily"], df["lead_time_days"], 0.95
    ).round(0)

    df["safety_stock_99"] = compute_safety_stock(
        df["demand_std_daily"], df["lead_time_days"], 0.99
    ).round(0)

    # ── Reorder Points ────────────────────────────────────────────────────────
    df["rop_95"] = compute_reorder_point(
        df["avg_daily_sales"], df["lead_time_days"], df["safety_stock_95"]
    ).round(0)

    df["rop_99"] = compute_reorder_point(
        df["avg_daily_sales"], df["lead_time_days"], df["safety_stock_99"]
    ).round(0)

    # ── Cost Comparison ───────────────────────────────────────────────────────
    # Current policy (use existing reorder_point as proxy for order qty)
    df["current_order_qty"] = df["reorder_point"] * 0.5  # rough estimate

    df["current_total_cost"] = compute_total_annual_cost(
        df["current_stock"], df["current_order_qty"],
        df["annual_demand"], df["ordering_cost"], df["holding_cost_per_unit"]
    )

    df["optimal_total_cost"] = compute_total_annual_cost(
        df["safety_stock_95"] + df["eoq"] / 2, df["eoq"],
        df["annual_demand"], df["ordering_cost"], df["holding_cost_per_unit"]
    )

    df["cost_savings"]         = (df["current_total_cost"] - df["optimal_total_cost"]).round(2)
    df["cost_savings_pct"]     = ((df["cost_savings"] / df["current_total_cost"]) * 100).round(2)
    df["recommendation"]       = np.where(
        df["cost_savings"] > 0,
        "Switch to EOQ policy",
        "Current policy is near-optimal"
    )

    # ── Summary Metrics ───────────────────────────────────────────────────────
    total_current = df["current_total_cost"].sum()
    total_optimal = df["optimal_total_cost"].sum()
    total_savings = df["cost_savings"].sum()
    savings_pct   = total_savings / total_current * 100

    print(f"\n  Optimization Results:")
    print(f"    Products analysed:      {len(df)}")
    print(f"    Current annual cost:    ${total_current:,.0f}")
    print(f"    Optimal annual cost:    ${total_optimal:,.0f}")
    print(f"    Potential savings:      ${total_savings:,.0f} ({savings_pct:.1f}%)")
    print(f"    Avg EOQ:                {df['eoq'].mean():.0f} units")
    print(f"    Avg Safety Stock (95%): {df['safety_stock_95'].mean():.0f} units")

    # Save results
    output_cols = [
        "product_id", "category", "avg_daily_sales", "annual_demand",
        "lead_time_days", "unit_cost", "ordering_cost", "holding_cost_per_unit",
        "eoq", "safety_stock_95", "safety_stock_99", "rop_95", "rop_99",
        "current_stock", "current_order_qty", "current_total_cost",
        "optimal_total_cost", "cost_savings", "cost_savings_pct", "recommendation",
    ]
    df[output_cols].to_csv(os.path.join(MODELS_DIR, "inventory_optimization.csv"), index=False)

    metrics = {
        "total_products": len(df),
        "total_current_cost": round(total_current, 2),
        "total_optimal_cost": round(total_optimal, 2),
        "total_savings": round(total_savings, 2),
        "savings_pct": round(savings_pct, 2),
        "avg_eoq": round(float(df["eoq"].mean()), 1),
        "avg_safety_stock_95pct": round(float(df["safety_stock_95"].mean()), 1),
    }
    with open(os.path.join(MODELS_DIR, "inventory_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"\n  ✅ Results saved to data/models/inventory_optimization.csv")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
