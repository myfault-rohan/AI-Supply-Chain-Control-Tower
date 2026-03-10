# AI Supply Chain Control Tower

An AI-powered platform for monitoring and optimizing supply chains using real-time data, machine learning, and analytics.

This system simulates a real enterprise supply chain platform used by manufacturing, logistics, and energy companies.

---

## Problem

Many companies struggle with:

• Inventory shortages  
• Demand spikes  
• Supplier delays  
• Poor supply chain visibility  

These problems can lead to production delays and financial losses.

The **AI Supply Chain Control Tower** helps detect and predict these risks.

---

## Features

### Real-Time Monitoring
Track inventory and demand using streaming data.

### Demand Forecasting
Predict product demand using machine learning models.

### Stockout Detection
Automatically identify products at risk of running out.

### Reorder Optimization
Recommend optimal reorder quantities.

### Supplier Performance Analytics
Analyze supplier reliability and delivery delays.

### Warehouse Utilization Analytics
Monitor warehouse capacity and utilization.

### Cost Analytics
Estimate financial impact of supply chain risks.

### Global Risk Dashboard
Executive overview of supply chain health.

### AI Supply Chain Advisor
Ask questions about supply chain status.

### Scenario Simulation
Simulate supply chain disruptions and demand changes.

### Automated Daily Risk Reports
Generate downloadable reports for managers.

---

## System Architecture

```text
User Dashboard (Streamlit)
↓
FastAPI Backend
↓
Machine Learning + Risk Engine
↓
Spark Processing
↓
Kafka Streaming
↓
Supply Chain Data
```

---

## Technology Stack

| Layer | Technology |
|------|-------------|
| Frontend | Streamlit |
| Backend | FastAPI |
| Streaming | Apache Kafka |
| Processing | Apache Spark |
| Machine Learning | Python, Scikit-learn, XGBoost |
| Visualization | Plotly |
| Data Processing | Pandas |

---

## Project Structure

```text
AI-Supply-Chain-Control-Tower
│
├── backend
├── dashboard
├── stream_pipeline
├── spark_processing
├── feature_engineering
├── risk_engine
├── alerts
├── reporting
├── dataset
├── reports
└── docs
```

---

## Setup Instructions

Install dependencies:

```bash
pip install -r requirements.txt
```

---

### Start Kafka

```bash
zookeeper-server-start.bat ....\config\zookeeper.properties
```
```bash
kafka-server-start.bat ....\config\server.properties
```

---

### Start Spark Streaming

```bash
python spark_processing\spark_streaming_processor.py
```

---

### Start Backend API

```bash
uvicorn backend.api_server:app --reload
```

---

### Start Dashboard

```bash
streamlit run dashboard/dashboard_app.py
```

---

### Start Kafka Producer

```bash
python stream_pipeline\kafka_producer.py
```

---

## Example Use Cases

The platform can monitor supply chains for:

• Manufacturing companies  
• Logistics companies  
• Retail distribution networks  
• Energy and oil supply chains  

Example insight:

```text
Product: Diesel
Warehouse: Mumbai Terminal
Stockout risk: 4 days
Recommended reorder: 9000 units
```

---

## Demo Dataset

A sample dataset is included in:

`dataset/demo_data/`

Files:

- `inventory.csv`
- `sales.csv`
- `suppliers.csv`
- `shipments.csv`
- `warehouses.csv`

You can copy these files into the `dataset/` folder to run the system.

---

## Dashboard Preview

Example dashboard panels:

• **Global Supply Chain Risk Overview**: High-level health metrics.  
• **Live Inventory Monitor**: Real-time stock tracking from Spark.  
• **Supplier Performance Analytics**: reliability and lead-time analysis.  
• **Warehouse Utilization**: Capacity and distribution tracking.  
• **Cost Analytics**: Financial impact of supply chain disruptions.  

*(Screenshots can be added here once available)*

---

## Future Improvements

• Cloud deployment (AWS / GCP)  
• Mobile dashboard  
• Advanced ML forecasting models  
• Automated notification system  

---

## License

This project is for educational and research purposes.
