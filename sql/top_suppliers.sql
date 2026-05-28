-- sql/top_suppliers.sql
-- Purpose: Identify top and worst performing suppliers based on reliability score and delay rates.
-- Useful for supply chain managers to negotiate contracts or find alternative sources.

SELECT 
    supplier_id,
    supplier_name,
    status,
    reliability_score,
    delay_rate,
    lead_time_days,
    CASE 
        WHEN reliability_score >= 95 AND delay_rate < 0.05 THEN 'Tier 1 - Excellent'
        WHEN reliability_score >= 85 AND delay_rate < 0.15 THEN 'Tier 2 - Good'
        WHEN reliability_score >= 70 AND delay_rate < 0.25 THEN 'Tier 3 - Needs Improvement'
        ELSE 'Tier 4 - High Risk'
    END AS supplier_tier
FROM 
    suppliers
ORDER BY 
    reliability_score DESC, 
    delay_rate ASC;
