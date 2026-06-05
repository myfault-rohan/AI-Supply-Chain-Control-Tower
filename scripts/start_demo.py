"""
One-command demo launcher for the AI Supply Chain Control Tower.
Generates synthetic data, seeds database tables, trains all machine learning models,
runs the data processing pipeline, starts the FastAPI backend, and launches the Streamlit dashboard.
"""
import subprocess
import sys
import os
import time
import shutil
import tempfile

# Fix Matplotlib config warning — use a writable temp dir
os.environ.setdefault("MPLCONFIGDIR", tempfile.mkdtemp(prefix="mpl_"))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")


def run_python_script(script_path, args=[], optional=False):
    """
    Utility to run a python script using the current python executable.
    If optional=True, a failure prints a warning but does NOT stop the demo.
    """
    cmd = [sys.executable, script_path] + args
    print(f"  Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        if optional:
            print(f"  ⚠️  Optional step failed (continuing): {script_path} — {e}")
            return False
        else:
            raise


def main():
    print("=" * 65)
    print("  AI SUPPLY CHAIN CONTROL TOWER — SYSTEM SETUP & DEMO LAUNCHER")
    print("=" * 65)

    # Kill any lingering uvicorn / streamlit processes that may be locking the DB
    print("  Stopping any previously running servers...")
    # Kill any process on port 8000 (uvicorn backend)
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True
        )
        for line in result.stdout.splitlines():
            if ":8000" in line and "LISTENING" in line:
                parts = line.strip().split()
                pid = parts[-1]
                subprocess.run(["taskkill", "/F", "/PID", pid],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"  Killed process on port 8000 (PID {pid})")
    except Exception:
        pass

    # Kill any process on port 8501 (streamlit)
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True
        )
        for line in result.stdout.splitlines():
            if ":8501" in line and "LISTENING" in line:
                parts = line.strip().split()
                pid = parts[-1]
                subprocess.run(["taskkill", "/F", "/PID", pid],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"  Killed process on port 8501 (PID {pid})")
    except Exception:
        pass

    time.sleep(2)  # Give OS time to release file handles

    # Remove existing database to prevent unique constraint errors on repeated runs
    for db_path in ["dataset/app.db", "app.db"]:
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
                print(f"  Cleared old database: {db_path}")
            except PermissionError:
                print(f"  WARNING: Could not delete {db_path} — will use upsert seeding instead.")



    # 1. Generate Synthetic Data
    print("\n[1/7] Generating synthetic supply chain data...")
    run_python_script("data_simulator/generate_supply_chain_data.py")

    # 2. Seed Database and Workspace Directories
    print("\n[2/7] Seeding SQLite database and workspace directories...")
    os.makedirs("dataset/synthetic", exist_ok=True)
    os.makedirs("dataset/workspaces/admin", exist_ok=True)
    os.makedirs("dataset/workspaces/default", exist_ok=True)
    os.makedirs("dataset/processed files", exist_ok=True)

    # Copy files to proper locations
    data_files = ["sales.csv", "products.csv", "suppliers.csv", "shipments.csv", "warehouses.csv", "inventory.csv"]
    for f in data_files:
        src = f"dataset/{f}"
        if os.path.exists(src):
            shutil.copy(src, f"dataset/synthetic/{f}")
            shutil.copy(src, f"dataset/workspaces/admin/{f}")
            shutil.copy(src, f"dataset/workspaces/default/{f}")
            print(f"  Copied {f} to workspaces and synthetic folder.")

    run_python_script("scripts/seed_admin.py")
    run_python_script("scripts/seed_sample_data.py", ["--dir", "dataset/synthetic"])

    # 3. Train Machine Learning Models
    print("\n[3/7] Training Machine Learning Models...")
    print("  [3a] XGBoost Demand Forecaster + SHAP...")
    run_python_script("ml_models/demand_forecaster.py")

    print("  [3b] PyOD Anomaly Detector...")
    run_python_script("ml_models/anomaly_detector.py")

    print("  [3c] Supplier Risk Model (Optuna + XGBoost)...")
    run_python_script("ml_models/supplier_risk_model.py")

    print("  [3d] Prophet Time-Series Forecaster (optional — may fail on Windows without C++ compiler)...")
    run_python_script("ml_models/prophet_forecaster.py", optional=True)

    print("  [3e] LSTM Deep Learning Forecaster (optional — requires neuralforecast)...")
    run_python_script("ml_models/lstm_forecaster.py", optional=True)

    # 4. Run Pandas Processing Pipeline
    print("\n[4/7] Running data processing pipeline for admin...")
    run_python_script("backend/pandas_processor.py", ["admin"])

    # 5. Start FastAPI Backend in Background
    print("\n[5/7] Starting FastAPI backend server in background (port 8000)...")
    backend_proc = subprocess.Popen([
        sys.executable, "-m", "uvicorn", "backend.api_server:app",
        "--host", "127.0.0.1", "--port", "8000"
    ])

    # Wait for the backend to start
    time.sleep(4)

    # 6. Verify backend is alive
    print("\n[6/7] Verifying backend is responding...")
    import urllib.request
    for attempt in range(5):
        try:
            urllib.request.urlopen("http://127.0.0.1:8000/api/v1/health", timeout=3)
            print("  Backend is live at http://127.0.0.1:8000")
            break
        except Exception:
            if attempt < 4:
                print(f"  Waiting for backend... ({attempt + 1}/5)")
                time.sleep(2)
            else:
                print("  WARNING: Backend health check timed out. Dashboard may show connection errors.")

    # 7. Start Streamlit Dashboard
    print("\n[7/7] Launching Streamlit dashboard...")
    print()
    print("=" * 65)
    print("  SYSTEM FULLY INITIALIZED!")
    print("  API Backend: http://127.0.0.1:8000")
    print("  API Docs:    http://127.0.0.1:8000/docs")
    print("  Dashboard:   http://localhost:8501")
    print()
    print("  Login with: admin / admin123")
    print("  Press Ctrl+C to stop all servers.")
    print("=" * 65)
    print()

    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "dashboard/dashboard_app.py",
            "--browser.gatherUsageStats=false",
            "--server.headless=true",
            "--server.address=127.0.0.1",
            "--server.port=8501"
        ], check=True)
    except KeyboardInterrupt:
        print("\nStopping demo...")
    finally:
        print("Terminating FastAPI backend...")
        backend_proc.terminate()
        backend_proc.wait()
        print("Demo stopped cleanly.")


if __name__ == "__main__":
    main()
