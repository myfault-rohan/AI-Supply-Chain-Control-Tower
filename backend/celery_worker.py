"""
Celery Task Queue Worker
Handles long-running tasks like ML retraining and report generation
in the background using Redis as the message broker.
"""

import os
import sys
from celery import Celery
import logging

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

REDIS_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")

app = Celery(
    "supply_chain_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True
)

logger = logging.getLogger(__name__)


@app.task(bind=True, name="train_ml_models")
def train_ml_models(self):
    """Background task to retrain the ML demand forecasting and risk models."""
    logger.info("Starting background ML retraining pipeline...")

    try:
        # Update task state
        self.update_state(state="PROGRESS", meta={"step": "demand_forecaster", "progress": 0})
        from ml_models.demand_forecaster import main as train_demand
        train_demand()
        logger.info("Demand forecaster retrained successfully.")

        self.update_state(state="PROGRESS", meta={"step": "anomaly_detector", "progress": 33})
        from ml_models.anomaly_detector import main as train_anomaly
        train_anomaly()
        logger.info("Anomaly detector retrained successfully.")

        self.update_state(state="PROGRESS", meta={"step": "supplier_risk_model", "progress": 66})
        from ml_models.supplier_risk_model import main as train_risk
        train_risk()
        logger.info("Supplier risk model retrained successfully.")

        logger.info("ML retraining complete.")
        return {"status": "success", "models": ["demand_forecaster", "anomaly_detector", "supplier_risk_model"]}

    except Exception as e:
        logger.error(f"ML retraining failed: {e}")
        return {"status": "error", "message": str(e)}


@app.task(bind=True, name="generate_executive_report")
def generate_executive_report(self):
    """Background task to generate the PDF executive report."""
    logger.info("Generating executive supply chain report...")

    try:
        from reporting.daily_report_generator import generate_pdf_report
        pdf_path = generate_pdf_report()
        logger.info(f"Report generated at {pdf_path}")
        return {"status": "success", "file": pdf_path}
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    app.start()
