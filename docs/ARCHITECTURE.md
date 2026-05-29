# 🧠 System Architecture

The **AI Supply Chain Control Tower** follows a modern, real-time data processing and machine learning pipeline architecture. The diagram below details the ingestion, engineering, model training, API serving, asynchronous task queuing, and AI advisor layers.

```mermaid
flowchart TD
    A[Data Generator / CSV Upload] --> B[Polars Processing Engine]
    B --> C[Feature Engineering Pipeline]
    C --> D[XGBoost Forecaster]
    C --> E[Prophet Forecaster]
    C --> F[LSTM NeuralForecast]
    C --> G[PyOD Anomaly Detector]
    D & E & F & G --> H[Processed Dataset (SQLite / Parquet)]
    H --> I[FastAPI Backend Server]
    I --> J[Streamlit Dashboard Interface]
    I --> K[PDF Report Generator]
    I --> L[Celery Task Queue]
    L --> M[Redis Broker / Backend Cache]
    J --> N[AI Advisor Panel - RAG + PydanticAI]
    N --> O[LlamaIndex + ChromaDB Vector Store]
```

---

## Component Details

### 1. Ingestion & Preprocessing
* **Polars Engine**: Handles core operations using high-performance, multithreaded columnar dataframes instead of Pandas.
* **Data Generator**: A simulation script using Faker to generate synthetic supply chain tables (sales, shipments, suppliers, products, inventory).

### 2. Machine Learning Suite
* **XGBoost Regressor**: Standard tabular model for predicting daily product sales (15 engineered features including lags, rolling windows, and supplier risks).
* **Prophet (Meta)**: Models daily demand capturing weekly and monthly seasonal trends.
* **LSTM (NeuralForecast)**: Deep learning recurrence-based model for complex sequential prediction.
* **PyOD ECOD (Anomaly Detection)**: Unsupervised anomaly detection on inventory levels and delivery delay rates.
* **SHAP Explainability**: Rebuilds feature trees to generate beeswarm and single-waterfall plots, making model forecasts transparent.

### 3. API & Middleware (FastAPI)
* **FastAPI Server**: Fully asynchronous backend exposing RESTful endpoints with SlowAPI rate limiting.
* **SQLAlchemy 2.0 & Alembic**: Object-relational mapping and database migrations.
* **Redis Caching**: Caching using `fastapi-cache2` on high-traffic GET endpoints (e.g. inventory metrics, supplier delay analysis).

### 4. Frontend & Presentation (Streamlit)
* **Streamlit App**: Interactive dark-themed, glassmorphic layout displaying real-time metrics, risk maps, interactive Plotly visualizations, SimPy-powered simulation experiments, and the AI Advisor.

### 5. Asynchronous Task Queue
* **Celery & Redis**: Background job worker that offloads heavy ML retraining operations from the main HTTP thread, allowing asynchronous non-blocking model training.

### 6. AI Advisor (RAG Panel)
* **PydanticAI & LlamaIndex**: Retrieves contextual information from database schemas and vector-indexed PDF manuals to answer natural language supply chain queries.
