import requests

API_URL = "http://127.0.0.1:8000"
endpoints = [
    "/daily_report",
    "/global_risk_summary",
    "/cost_analysis",
    "/warehouse_utilization",
    "/supplier_performance",
    "/live_inventory"
]

print("--- API Verification ---")
for ep in endpoints:
    try:
        r = requests.get(f"{API_URL}{ep}")
        print(f"{ep}: {r.status_code}")
        if r.status_code != 200:
            print(f"  Error: {r.text}")
    except Exception as e:
        print(f"{ep}: Failed to connect ({e})")
