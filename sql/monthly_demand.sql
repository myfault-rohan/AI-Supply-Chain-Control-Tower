-- sql/monthly_demand.sql
-- Purpose: Analyze predicted demand against current stock to find upcoming shortages.
-- Joins products and forecasts tables to find high-risk demand spikes.

SELECT 
    p.product_id,
    p.product_name,
    p.current_stock,
    f.predicted_demand,
    f.avg_daily_sales,
    f.days_until_stockout,
    f.demand_spike,
    f.confidence_score,
    CASE
        WHEN f.days_until_stockout < 7 THEN 'Immediate Action Required ( < 7 days)'
        WHEN f.days_until_stockout < 14 THEN 'Short Term Risk ( < 14 days)'
        WHEN f.days_until_stockout < 30 THEN 'Medium Term Planning ( < 30 days)'
        ELSE 'Adequate Supply ( 30+ days )'
    END AS stockout_timeline
FROM 
    products p
JOIN 
    forecasts f ON p.id = f.product_id
WHERE 
    f.days_until_stockout < 30 OR f.demand_spike = 1
ORDER BY 
    f.days_until_stockout ASC;
