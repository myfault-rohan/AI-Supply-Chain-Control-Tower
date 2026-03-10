# System Flow

1. **Date Entry**: Data enters the system through Kafka events or uploaded datasets.
2. **Spark Processing**: Spark processes streaming events and generates analytics datasets.
3. **Machine Learning**: Machine learning models calculate demand forecasts.
4. **Risk Detection**: The risk engine detects supply chain issues and bottlenecks.
5. **API Layer**: FastAPI exposes analytics via REST APIs.
6. **Visualization**: Streamlit dashboard visualizes results in real-time.

### Pipeline Diagram
```text
Kafka → Spark → ML Analytics → FastAPI → Dashboard
```
