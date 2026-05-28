-- sql/inventory_turnover.sql
-- Purpose: Analyze current stock levels compared to safety stock and reorder points.
-- Highlights products that are currently below safety stock limits.

SELECT 
    p.product_id,
    p.product_name,
    p.warehouse_id,
    p.current_stock,
    p.safety_stock,
    p.reorder_point,
    (p.current_stock - p.safety_stock) AS stock_buffer,
    CASE 
        WHEN p.current_stock <= 0 THEN 'OUT OF STOCK'
        WHEN p.current_stock <= p.safety_stock THEN 'CRITICAL - Below Safety Stock'
        WHEN p.current_stock <= p.reorder_point THEN 'WARNING - Needs Reorder'
        ELSE 'HEALTHY'
    END AS inventory_health_status
FROM 
    products p
ORDER BY 
    stock_buffer ASC;
