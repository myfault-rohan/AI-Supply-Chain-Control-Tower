from dotenv import load_dotenv
import os

load_dotenv()

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
DATASET_DIR = os.getenv("DATASET_DIR", "dataset")

# JWT Configuration - JWT_SECRET required in production; falls back to insecure default in CI/test
_jwt_secret = os.getenv("JWT_SECRET")
if not _jwt_secret:
    import warnings
    warnings.warn(
        "JWT_SECRET not set — using insecure default. Set JWT_SECRET in .env for production.",
        stacklevel=2,
    )
    _jwt_secret = "ci-test-only-insecure-secret-do-not-use-in-production"
JWT_SECRET = _jwt_secret
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))
