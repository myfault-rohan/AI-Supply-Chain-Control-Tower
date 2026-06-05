import sys
sys.path.insert(0, 'D:\\AI-Supply-Chain-Control-Tower')
try:
    from backend import api_server
    print("OK - api_server imported successfully")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
