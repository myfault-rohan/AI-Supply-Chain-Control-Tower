import pandas as pd
import time
import os
import glob

# Configuration
INPUT_PATH = "dataset/live_supply_chain"
OUTPUT_FILE = "dataset/live_alerts.csv"
CHECK_INTERVAL = 10  # seconds

def load_latest_data(directory):
    """
    Loads the latest CSV data from the specified directory.
    Spark streaming writes multiple CSV files to the output directory.
    """
    if not os.path.exists(directory):
        return pd.DataFrame()
    
    # Get all CSV files in the directory
    files = glob.glob(os.path.join(directory, "*.csv"))
    if not files:
        return pd.DataFrame()
    
    # Load and combine all CSV files (or just the latest one if preferred)
    # For a live stream, we typically want to process the newest records.
    # Since Spark appends, we'll read all and handle duplicates if necessary,
    # or just read the most recent file.
    
    dfs = []
    for f in files:
        try:
            temp_df = pd.read_csv(f)
            dfs.append(temp_df)
        except Exception as e:
            print(f"Error reading {f}: {e}")
            
    if not dfs:
        return pd.DataFrame()
        
    return pd.concat(dfs, ignore_index=True)

def detect_alerts(df):
    """
    Detects stockout risks based on inventory_days.
    """
    alerts = []
    
    if df.empty:
        return alerts
        
    for _, row in df.iterrows():
        inventory_days = row.get('inventory_days', 999)
        alert_level = None
        
        if inventory_days < 3:
            alert_level = "CRITICAL"
        elif 3 <= inventory_days <= 7:
            alert_level = "WARNING"
            
        if alert_level:
            alert_msg = {
                "product_id": row.get('product_id'),
                "warehouse_id": row.get('warehouse_id'),
                "current_stock": row.get('current_stock'),
                "inventory_days": round(inventory_days, 2),
                "alert_level": alert_level,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            alerts.append(alert_msg)
            
    return alerts

def save_alerts(alerts, output_file):
    """
    Saves alerts to a CSV file. Appends to existing if it exists.
    """
    if not alerts:
        return
        
    new_alerts_df = pd.DataFrame(alerts)
    
    if os.path.exists(output_file):
        try:
            existing_df = pd.read_csv(output_file)
            updated_df = pd.concat([existing_df, new_alerts_df], ignore_index=True)
            # Optional: Deduplicate or limit size
            updated_df.to_csv(output_file, index=False)
        except Exception:
            new_alerts_df.to_csv(output_file, index=False)
    else:
        new_alerts_df.to_csv(output_file, index=False)

def main():
    print(f"Starting Alert Engine... Monitoring {INPUT_PATH}")
    print(f"Check interval: {CHECK_INTERVAL} seconds")
    
    while True:
        try:
            # 1. Load data
            df = load_latest_data(INPUT_PATH)
            
            # 2. Detect alerts
            alerts = detect_alerts(df)
            
            # 3. Print and Save
            if alerts:
                print(f"\n[{time.strftime('%H:%M:%S')}] Detected {len(alerts)} alerts:")
                for alert in alerts:
                    print(f"  - {alert['alert_level']}: Product {alert['product_id']} at Warehouse {alert['warehouse_id']} "
                          f"has {alert['inventory_days']} days of inventory left (Stock: {alert['current_stock']})")
                
                save_alerts(alerts, OUTPUT_FILE)
            else:
                print(".", end="", flush=True) # Heartbeat
                
        except Exception as e:
            print(f"\nError in alert loop: {e}")
            
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
