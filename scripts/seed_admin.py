#!/usr/bin/env python3
"""
Seed an admin user into the Phase-1 database.

Usage: python scripts/seed_admin.py
Environment variables:
  ADMIN_USERNAME - default: 'admin'
  ADMIN_EMAIL    - default: 'admin@example.com'
  ADMIN_PASSWORD - default: 'ChangeMe123!'
"""
import os
import sys
# Ensure project root is on sys.path when executed from the scripts folder
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.database import SessionLocal, init_db
from backend.auth import get_user_by_username, create_user


def main():
    init_db()
    username = os.getenv("ADMIN_USERNAME", "admin")
    email = os.getenv("ADMIN_EMAIL", "admin@example.com")
    password = os.getenv("ADMIN_PASSWORD", "ChangeMe123!")
    with SessionLocal() as db:
        existing = get_user_by_username(db, username)
        if existing:
            print(f"Admin user '{username}' already exists (id={existing.id})")
            return
        user = create_user(db, username=username, email=email, password=password, role="admin")
        print(f"Created admin user '{user.username}' (id={user.id}) — change the password immediately.")


if __name__ == "__main__":
    main()
