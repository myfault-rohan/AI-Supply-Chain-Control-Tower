import json
import os
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import JWTError, jwt
from config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_MINUTES

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(plain): 
    return pwd_context.hash(plain)

def verify_password(plain, hashed): 
    return pwd_context.verify(plain, hashed)

def load_users():
    base_path = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_path, "database", "users.json")
    if not os.path.exists(file_path): return []
    with open(file_path) as f: return json.load(f)

def save_users(users):
    base_path = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_path, "database", "users.json")
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as f: json.dump(users, f, indent=2)

def authenticate(username, password):
    users = load_users()
    for u in users:
        if u["username"] == username and verify_password(password, u.get("password_hash", "")):
            return True
    return False

def create_access_token(data: dict, expires_minutes: int = None):
    to_encode = data.copy()
    expires = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes or JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expires})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("sub") is None:
            raise JWTError("Token missing 'sub'")
        return payload
    except JWTError:
        raise
