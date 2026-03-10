import requests
import os

API_URL = "http://127.0.0.1:8000"
USERNAME = "admin"
DATASET_DIR = "dataset/demo_data"

def test_multi_upload():
    print("--- Testing Multi-File Upload API ---")
    files_to_upload = ["inventory.csv", "sales.csv", "suppliers.csv", "shipments.csv", "warehouses.csv"]
    
    files_payload = []
    for filename in files_to_upload:
        file_path = os.path.join(DATASET_DIR, filename)
        if os.path.exists(file_path):
            files_payload.append(("files", (filename, open(file_path, "rb"), "text/csv")))
    
    if not files_payload:
        print("Error: No demo files found to upload.")
        return

    try:
        response = requests.post(
            f"{API_URL}/upload_data",
            params={"username": USERNAME},
            files=files_payload
        )
        
        print(f"Status Code: {response.status_code}")
        print("Response JSON:")
        print(response.json())
        
        if response.status_code == 200:
            print("\nSUCCESS: Multi-file upload and processing triggered.")
        else:
            print("\nFAILED: API returned error.")
            
    except Exception as e:
        print(f"FAILED: Connection error: {e}")

if __name__ == "__main__":
    test_multi_upload()
