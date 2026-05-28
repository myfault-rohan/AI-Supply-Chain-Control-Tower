-- sql/risk_ranking.sql
-- Purpose: Rank products based on the severity and number of active alerts.
-- Helps prioritize supply chain control tower operations.

SELECT 
    p.product_id,
    p.product_name,
    p.warehouse_id,
    COUNT(a.id) AS total_active_alerts,
    SUM(CASE WHEN a.severity = 'CRITICAL' THEN 1 ELSE 0 END) AS critical_alerts,
    SUM(CASE WHEN a.severity = 'WARNING' THEN 1 ELSE 0 END) AS warning_alerts,
    GROUP_CONCAT(DISTINCT a.alert_type) AS alert_types
FROM 
    products p
JOIN 
    alerts a ON p.id = a.product_id
WHERE 
    a.is_acknowledged = 0
GROUP BY 
    p.product_id, p.product_name, p.warehouse_id
HAVING 
    total_active_alerts > 0
ORDER BY 
    critical_alerts DESC, 
    warning_alerts DESC,
    total_active_alerts DESC;
