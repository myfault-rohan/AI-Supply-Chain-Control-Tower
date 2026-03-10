# System Data Flow

This document outlines the end-to-end data flow within the system.

## 1. Data Ingestion
- `kafka_producer.py` simulates real-time activity and sends events to Kafka topics (`inventory_updates`).

## 2. Real-time Processing
- `spark_streaming_processor.py` consumes data from Kafka.
- Features are engineered on-the-fly (e.g., rolling averages, demand volatility).
- Results are saved to `dataset/live_supply_chain`.

## 3. Risk & AI Analysis
- The `Risk Engine` runs periodically to detect stockout risks based on current inventory and lead times.
- The `AI Advisor` uses the processed data to answer user queries via the API.

## 4. Visualization
- The `Streamlit Dashboard` polls the `FastAPI Backend` to display real-time metrics and charts.
