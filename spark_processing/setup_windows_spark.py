import os
import requests
import shutil

# Configuration
HADOOP_VERSION = "3.3.5"
BASE_URL = f"https://github.com/cdarlint/winutils/raw/master/hadoop-{HADOOP_VERSION}/bin/"
BINARIES = ["winutils.exe", "hadoop.dll"]

TARGET_DIR = os.path.join(os.getcwd(), "tmp", "hadoop", "bin")

def setup_hadoop_binaries():
    """Download and set up winutils.exe and hadoop.dll"""
    print(f"--- Setting up Hadoop {HADOOP_VERSION} binaries for Windows ---")
    
    if not os.path.exists(TARGET_DIR):
        print(f"Creating directory: {TARGET_DIR}")
        os.makedirs(TARGET_DIR, exist_ok=True)

    for binary in BINARIES:
        target_path = os.path.join(TARGET_DIR, binary)
        # Force download if file is 0 bytes or missing
        if os.path.exists(target_path) and os.path.getsize(target_path) > 0:
            print(f"Found valid {binary} ({os.path.getsize(target_path)} bytes). Skipping.")
            continue
            
        url = BASE_URL + binary
        print(f"Downloading {binary} from {url}...")
        try:
            # Use os.system with curl for robustness on Windows if requests fails or for 0-byte files
            cmd = f'curl -L -o "{target_path}" "{url}"'
            print(f"Running: {cmd}")
            exit_code = os.system(cmd)
            
            if exit_code == 0 and os.path.exists(target_path) and os.path.getsize(target_path) > 0:
                print(f"Successfully downloaded {binary} ({os.path.getsize(target_path)} bytes)")
            else:
                print(f"Failed to download {binary} via curl (exit code {exit_code}).")
                return False
        except Exception as e:
            print(f"Error downloading {binary}: {e}")
            return False

    print("\n--- Setup Complete ---")
    return True

if __name__ == "__main__":
    setup_hadoop_binaries()
