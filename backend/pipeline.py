import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend.pandas_processor import run_full_pipeline

def run_pipeline(username="default"):
    """Delegates to pandas_processor — no Spark required."""
    return run_full_pipeline(username)

if __name__ == "__main__":
    user = sys.argv[1] if len(sys.argv) > 1 else "default"
    print(run_pipeline(user))
