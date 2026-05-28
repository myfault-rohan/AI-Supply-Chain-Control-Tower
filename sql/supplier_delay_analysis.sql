-- sql/supplier_delay_analysis.sql
-- Purpose: Correlate supplier delay rates with reorder recommendations to identify 
-- if critical reorders are dependent on risky suppliers.

SELECT 
    r.product_id,
    r.reorder_quantity,
    r.stockout_risk,
    r.priority,
    r.supplier_lead_time,
    s.supplier_name,
    s.status AS supplier_status,
    s.reliability_score,
    s.delay_rate,
    (r.supplier_lead_time * (1 + s.delay_rate)) AS adjusted_expected_lead_time
FROM 
    reorder_recommendations r
-- Assuming a mapping exists between product and supplier. If not directly linked in schema, 
-- this query serves as a conceptual template for the data analyst to use when the mapping table exists.
-- For this schema, we simulate the join or join on a common attribute if one is added (e.g., primary_supplier_id in products).
CROSS JOIN 
    suppliers s 
WHERE 
    r.stockout_risk = 1 AND s.status = 'AT_RISK'
ORDER BY 
    r.priority DESC, 
    adjusted_expected_lead_time DESC
LIMIT 50;
