# Data Schema

## `inventory.csv`
- `product_id`: Unique identifier for the product
- `product_name`: Name of the product (e.g., Diesel, Petrol)
- `warehouse_id`: ID of the warehouse where stock is located
- `current_stock`: Current physical stock level
- `safety_stock`: Minimum stock level required as buffer
- `reorder_point`: Stock level at which a new order should be placed

## `sales.csv`
- `product_id`: Reference to product
- `date`: Sales transaction date
- `daily_sales`: Units sold on this date
- `region`: Sales region

## `suppliers.csv`
- `supplier_id`: Unique identifier for the supplier
- `supplier_name`: Name of the supplier
- `lead_time_days`: Average days for delivery
- `reliability_score`: Score based on historical performance

## `shipments.csv`
- `shipment_id`: Unique shipment ID
- `supplier_id`: Reference to supplier
- `product_id`: Reference to product
- `shipment_date`: Date shipped
- `expected_delivery`: Planned delivery date
- `actual_delivery`: Real arrival date
- `status`: Shipment status (Delivered, Delayed, In Transit)

## `warehouses.csv`
- `warehouse_id`: Unique identifier for the warehouse
- `warehouse_location`: Physical location (City/Terminal)
- `capacity`: Maximum storage capacity
