import pandas as pd
import os
import time

# Configuration
TEST_DIR = "dataset/live_supply_chain"
ALERTS_FILE = "dataset/live_alerts.csv"

def setup_test_data():
    """
    Creates mock inventory data in the live_supply_chain directory.
    """
    if not os.path.exists(TEST_DIR):
        os.makedirs(TEST_DIR)
        
    # Create a mock CSV with different inventory levels
    data = {
        "product_id": [101, 102, 103, 104],
        "warehouse_id": [1, 1, 2, 2],
        "current_stock": [50, 150, 250, 400],
        "daily_demand": [20, 30, 40, 50],
        "inventory_days": [2.5, 5.0, 6.25, 8.0] # <3 (CRITICAL), 5 (WARNING), 6.25 (WARNING), 8 (NONE)
    }
    
    df = pd.DataFrame(data)
    test_file = os.path.join(TEST_DIR, "part-00000-test.csv")
    df.to_csv(test_file, index=False)
    print(f"Created test data at {test_file}")

def verify_alerts():
    """
    Checks if the alerts were correctly generated in live_alerts.csv.
    """
    if not os.path.exists(ALERTS_FILE):
        print("Alerts file not found.")
        return False
        
    df = pd.read_csv(ALERTS_FILE)
    print("\nGenerated Alerts:")
    print(df)
    
    # Check for expected alerts
    critical_alerts = df[df['alert_level'] == 'CRITICAL']
    warning_alerts = df[df['alert_level'] == 'WARNING']
    
    if len(critical_alerts) >= 1 and len(warning_alerts) >= 2:
        print("\nVerification SUCCESS: Detected expected alerts.")
        return True
    else:
        print("\nVerification FAILED: Did not find expected alerts.")
        return False

if __name__ == "__main__":
    setup_test_data()
    # In a real scenario, we'd run alert_engine.py in the background
    # and then check the results. For this verification, we can just
    # test the logic by importing alert_engine or running it once.
    print("Test data is ready. Please run 'python alerts/alert_engine.py' and check the output.")
