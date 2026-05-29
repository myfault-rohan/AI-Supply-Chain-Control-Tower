# ============================================================
# AI Supply Chain Control Tower — Developer Makefile
# ============================================================

.PHONY: install demo train test clean

install:
	python -m pip install --upgrade pip
	pip install -r requirements-core.txt

demo:
	python scripts/start_demo.py

train-all:
	python scripts/generate_synthetic_data.py
	python ml_models/demand_forecaster.py
	python ml_models/prophet_forecaster.py
	python ml_models/anomaly_detector.py
	python ml_models/supplier_risk_model.py

test:
	pytest tests/ -v --tb=short

clean:
	python -c "import pathlib, shutil; [p.unlink() for p in pathlib.Path('.').rglob('*.pyc')]; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]"
