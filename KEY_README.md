# AI Supply Chain Control Tower — Key System Notes

## Important Data Locations

User uploaded data:
dataset/uploads/

Streaming data from Spark:
dataset/live_supply_chain/

Generated analytics:
dataset/

Daily reports:
reports/

---

## Important Scripts

Kafka Producer
stream_pipeline/kafka_producer.py

Spark Streaming Processor
spark_processing/spark_streaming_processor.py

FastAPI Server
backend/api_server.py

Dashboard
dashboard/dashboard_app.py

Daily Report Generator
reporting/daily_report_generator.py

---

## Terminals Required to Run System

1 Zookeeper  
2 Kafka Server  
3 Spark Streaming Processor  
4 FastAPI Backend  
5 Streamlit Dashboard  
6 Kafka Producer  

---

## Important API Endpoints

/inventory  
/demand_forecast  
/reorder_recommendations  
/supplier_performance  
/warehouse_utilization  
/cost_analysis  
/global_risk_summary  
/daily_report  
/live_inventory  

---

## User Data Upload

Users upload:

inventory.csv  
sales.csv  
suppliers.csv  
shipments.csv  
warehouses.csv  

Uploaded files stored in:

dataset/uploads/
