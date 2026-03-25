from dotenv import load_dotenv
import os

load_dotenv()

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
DATASET_DIR = os.getenv("DATASET_DIR", "dataset")

# JWT Configuration - JWT_SECRET is REQUIRED for security
_jwt_secret = os.getenv("JWT_SECRET")
if not _jwt_secret:
    raise RuntimeError(
        "JWT_SECRET environment variable is required. "
        "Set it in .env file or environment: JWT_SECRET=your-secure-random-secret"
    )
JWT_SECRET = _jwt_secret
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))
