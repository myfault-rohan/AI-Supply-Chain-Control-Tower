# AI-Powered Supply Chain Analytics & Forecasting Platform

![Python](https://img.shields.io/badge/Python-3.11-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-009688.svg?logo=fastapi)
![Streamlit](https://img.shields.io/badge/Streamlit-1.29.0-FF4B4B.svg?logo=streamlit)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0.23-red.svg)
![XGBoost](https://img.shields.io/badge/XGBoost-2.0-blue.svg)
![Prophet](https://img.shields.io/badge/Prophet-1.1-green.svg)
![Redis](https://img.shields.io/badge/Redis-Cache-DC382D.svg?logo=redis)

An enterprise-grade, multi-tenant AI Supply Chain Control Tower. It features a robust Python/FastAPI backend, Streamlit dashboard, and advanced ML forecasting (XGBoost + Prophet) with SHAP explainability.

---

## 🌟 Key Features

1. **Advanced Demand Forecasting**
   - **XGBoost Regressor**: Engineered 14+ features (inventory pressure, delay risk) for daily sales.
   - **Prophet (Time-Series)**: Captures weekly/monthly seasonality for daily demand forecasting.
   - **Model Comparison**: Compare MAE, RMSE, and MAPE between models in real-time.

2. **Explainable AI (XAI)**
   - **SHAP Integration**: Visualizes feature importance and summary plots, breaking the "black box" of XGBoost so supply chain managers understand *why* a stockout is predicted.

3. **Data Analyst Tooling**
   - **Analytical SQL Queries**: Built-in scripts for inventory turnover, risk ranking, and supplier delays.
   - **Jupyter EDA Notebooks**: Deep dives into supplier reliability, stock distribution, and overall risk.
   - **Faker Data Generation**: Instantly generate thousands of synthetic products, suppliers, and sales records for testing.

4. **Enterprise Backend Architecture**
   - **FastAPI**: Asynchronous API with JWT Authentication and structured error handling.
   - **SQLAlchemy 2.0 & Alembic**: Database ORM and automated schema migrations.
   - **Redis Caching**: Caches expensive API endpoints (e.g., dashboard KPIs) using `fastapi-cache2`.

---

## 🏗️ Tech Stack

| Layer | Technologies |
|-------|--------------|
| **Backend API** | FastAPI, Pydantic, JWT Auth |
| **Database** | SQLite (Phase 1) / PostgreSQL Ready, SQLAlchemy 2.0, Alembic |
| **Caching** | Redis, fastapi-cache2 |
| **Machine Learning** | XGBoost, Prophet, Scikit-Learn |
| **Explainability** | SHAP, Matplotlib |
| **Frontend UI** | Streamlit, Plotly, Pandas |
| **Testing/Ops** | Pytest, Docker Compose |

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.11+
- Redis Server (optional, but recommended for caching)
- Git

### 2. Installation
```bash
git clone https://github.com/myfault-rohan/AI-Supply-Chain-Control-Tower.git
cd AI-Supply-Chain-Control-Tower

# Create Virtual Environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\activate

# Install Dependencies
pip install -r requirements.txt
```

### 3. Generate Data & Train Models
```bash
# Generate synthetic dataset (Sales, Suppliers, Products)
python scripts/generate_synthetic_data.py

# Train XGBoost model and generate SHAP explainers
python ml_models/demand_forecaster.py

# Train Prophet Time-Series model
python ml_models/prophet_forecaster.py
```

### 4. Database Setup
```bash
# Run Alembic migrations to initialize the database schema
alembic upgrade head
```

### 5. Launch the Platform
```bash
# Start Redis (if installed locally via Docker)
docker run -d -p 6379:6379 redis

# Start FastAPI Backend (Port 8000)
uvicorn backend.api_server_phase1:app --reload

# Start Streamlit Dashboard (Port 8501)
# (Run in a new terminal)
streamlit run dashboard/app.py
```

---

## 📂 Project Structure

```text
AI-Supply-Chain-Control-Tower/
├── alembic/                # Database migrations
├── backend/                # FastAPI Application
│   ├── api_server_phase1.py  # Main API Entrypoint
│   ├── models.py           # SQLAlchemy Models
│   ├── auth.py             # JWT Security
│   └── database.py         # DB connection pool
├── dashboard/              # Streamlit Frontend UI
│   ├── app.py              # Main dashboard entrypoint
│   └── pages/              # UI Tabs (Analytics, AI Advisor, ML Explainability)
├── ml_models/              # Machine Learning Pipelines
│   ├── demand_forecaster.py # XGBoost + SHAP
│   └── prophet_forecaster.py# Prophet
├── notebooks/              # Jupyter EDA Notebooks
├── scripts/                # Data Generation & Utils
├── sql/                    # Analytical SQL Queries
└── tests/                  # Pytest suite
```

---

## 🛡️ License
MIT License
