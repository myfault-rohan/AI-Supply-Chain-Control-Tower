import subprocess
import time
import requests
import sys

def test_api():
    print("Starting FastAPI server...")
    server = subprocess.Popen(['python', 'backend/api_server.py'])
    time.sleep(5)
    
    success = True
    try:
        endpoints = ['inventory', 'demand_forecast', 'reorder_recommendations', 'alerts']
        for ep in endpoints:
            print(f"Testing /{ep}...")
            r = requests.get(f"http://127.0.0.1:8000/{ep}")
            if r.status_code == 200:
                print(f"  ✓ Status: {r.status_code}")
                data = r.json()
                print(f"  ✓ Received {len(data)} records")
            else:
                print(f"  ✗ Status: {r.status_code}")
                success = False
                
    except Exception as e:
        print(f"Verification failed: {e}")
        success = False
    finally:
        print("Stopping server...")
        server.terminate()
        server.wait()
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    test_api()
