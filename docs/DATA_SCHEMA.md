# Data Schema

This document describes the data models and schemas used in the system.

## 1. Input Datasets (CSV)
- **`inventory.csv`**: `product_id`, `warehouse_id`, `current_stock`, `reorder_level`
- **`suppliers.csv`**: `supplier_id`, `supplier_name`, `lead_time_days`, `reliability_score`
- **`sales.csv`**: `sale_id`, `product_id`, `units_sold`, `sale_date`

## 2. Kafka Event Schema
- **Topic**: `inventory_updates`
- **Format**: JSON
- **Fields**: `timestamp`, `product_id`, `warehouse_id`, `change_type`, `quantity`

## 3. Processed Data (Spark Output)
- **File**: `dataset/live_supply_chain`
- **Fields**: `product_id`, `warehouse_id`, `moving_avg_demand`, `demand_volatility`, `days_until_stockout`, `health_status`

## 4. Reports (CSV Output)
- **File**: `reports/daily_supply_chain_report.csv`
- **Fields**: `Report Date`, `Critical Products Count`, `Top Critical Item`, `Top Cost Impact Item`, `Worst Supplier`
