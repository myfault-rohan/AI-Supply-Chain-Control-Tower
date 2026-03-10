import json
import os

def load_users():
    # Adjusted path to handle runtime environment (Docker vs Local)
    base_path = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_path, "database", "users.json")
    
    if not os.path.exists(file_path):
        return []
        
    with open(file_path) as f:
        return json.load(f)

def authenticate(username, password):
    users = load_users()

    for user in users:
        if user["username"] == username and user["password"] == password:
            return True

    return False
