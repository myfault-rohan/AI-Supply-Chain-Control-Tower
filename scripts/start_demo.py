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

def run_python_script(script_path, args=[]):
    """Utility to run a python script using the current python executable."""
    cmd = [sys.executable, script_path] + args
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

def main():
    print("=" * 65)
    print("🏭  AI SUPPLY CHAIN CONTROL TOWER — SYSTEM SETUP & DEMO LAUNCHER  🏭")
    print("=" * 65)

    # 1. Generate Synthetic Data
    print("\n[1/6] Generating synthetic supply chain data...")
    run_python_script("data_simulator/generate_supply_chain_data.py")

    # 2. Seed Database and Workspace Directories
    print("\n[2/6] Seeding SQLite database and workspace directories...")
    # Initialize workspace folders
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

    # Seed database
    run_python_script("scripts/seed_admin.py")
    run_python_script("scripts/seed_sample_data.py", ["--dir", "dataset/synthetic"])

    # 3. Train Machine Learning Models
    print("\n[3/6] Training Machine Learning Models (XGBoost, Prophet, PyOD Anomaly, Supplier Risk)...")
    run_python_script("ml_models/demand_forecaster.py")
    run_python_script("ml_models/anomaly_detector.py")
    run_python_script("ml_models/supplier_risk_model.py")
    run_python_script("ml_models/prophet_forecaster.py")

    # 4. Run Pandas Processing Pipeline
    print("\n[4/6] Running data processing pipeline for admin...")
    run_python_script("backend/pandas_processor.py", ["admin"])

    # 5. Start FastAPI Backend in Background
    print("\n[5/6] Starting FastAPI backend server in background...")
    backend_proc = subprocess.Popen([
        sys.executable, "-m", "uvicorn", "backend.api_server:app",
        "--host", "127.0.0.1", "--port", "8000"
    ])
    
    # Wait for the backend to start
    time.sleep(3)

    # 6. Start Streamlit Dashboard
    print("\n[6/6] Launching Streamlit dashboard...")
    print("\n✅ System fully initialized!")
    print("   FastAPI backend is running in background (port 8000)")
    print("   API Docs: http://127.0.0.1:8000/docs")
    print("   Dashboard will open at http://localhost:8501")
    print("\nPress Ctrl+C in this terminal to stop all servers.\n")

    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "dashboard/dashboard_app.py"
        ], check=True)
    except KeyboardInterrupt:
        print("\nStopping setup...")
    finally:
        print("Terminating FastAPI backend...")
        backend_proc.terminate()
        backend_proc.wait()
        print("Setup stopped cleanly.")

if __name__ == "__main__":
    main()
