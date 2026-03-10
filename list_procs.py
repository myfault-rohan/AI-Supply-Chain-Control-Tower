import psutil
import os

def list_python_processes():
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'python' in proc.info['name'].lower():
                print(f"PID: {proc.info['pid']}, CMD: {proc.info['cmdline']}")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

if __name__ == "__main__":
    list_python_processes()
