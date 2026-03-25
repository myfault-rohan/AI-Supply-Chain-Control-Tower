# AI Supply Chain Control Tower

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-009688.svg?logo=fastapi)
![Streamlit](https://img.shields.io/badge/Streamlit-1.32.0-FF4B4B.svg?logo=streamlit)
![Pandas](https://img.shields.io/badge/Pandas-2.2.2-150458.svg?logo=pandas)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## Overview

An enterprise-grade, multi-tenant AI Supply Chain Control Tower built with FastAPI and Streamlit. It features a robust Python/Pandas data processing engine that handles risk detection, inventory forecasting, supplier performance scoring, and warehouse utilization tracking. Includes an Anthropic-powered AI advisor and Monte Carlo simulation lab.

## Feature Status

| Feature | Status | Description |
|---------|--------|-------------|
| **JWT Authentication** | Complete | Secure login and API protection via HS256 JWTs |
| **Data Engine** | Complete | Python/Pandas based pure analytics pipeline |
| **AI Advisor** | Complete | Integrated with Claude for live actionable insights |
| **Simulation Lab** | Complete | Monte Carlo simulation with visual ROI impact |
| **Executive PDF Export** | Complete | Live snapshot exporting via ReportLab |
| **Data Quality Monitor** | Complete | Automated schema validation and suggestions |
| **Multi-tenant UI** | Complete | Workspace-based file isolation and management |
| **i18n (EN/JA)** | Complete | Dynamic language toggling across the dashboard |

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure Environment:
```bash
cp .env.example .env
# Generate a secure JWT secret:
python -c "import secrets; print(f'JWT_SECRET={secrets.token_urlsafe(32)}')"
# Add the output to your .env file, along with your Anthropic API key
```

3. Launch System:
```powershell
.\start_system.ps1
```
This will start both the FastAPI backend (Port 8000) and the Streamlit dashboard (Port 8501).

## Environment Variables (.env)

| Variable | Required | Purpose |
|----------|----------|---------|
| `JWT_SECRET` | **Yes** | Secret key for JWT signature (generate with `secrets.token_urlsafe(32)`) |
| `ANTHROPIC_API_KEY` | For AI features | API key for the AI Advisor |
| `API_URL` | No (default: `http://127.0.0.1:8000`) | Backend connection URL for Streamlit |
| `DATASET_DIR` | No (default: `dataset`) | Root path for workspaces and generated files |
| `JWT_ALGORITHM` | No (default: `HS256`) | Hashing algorithm for tokens |
| `JWT_EXPIRE_MINUTES` | No (default: `480`) | Token expiration duration (8 hours) |

## API Reference

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/api/v1/token` | `POST` | Exchange username/password for JWT | No |
| `/upload_data` | `POST` | Upload CSV/JSON data into workspace | Yes |
| `/export/pdf` | `GET` | Download executive summary PDF report | Yes |
| `/api/v1/health` | `GET` | System health and API status check | No |
| `/workspace_files` | `GET` | List files in your workspace | Yes |
| `/data_explorer` | `GET` | Preview workspace file contents | Yes |
| `/data-quality` | `GET` | Get data quality analysis | Yes |
| `/admin/system_health` | `GET` | System metrics | Yes |
| `/admin/clear_workspace` | `POST` | Clear your workspace | Yes |
| `/global_risk_summary` | `GET` | Aggregated risk overview | No |
| `/daily_report` | `GET` | Latest daily report | No |
