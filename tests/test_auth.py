import pytest
from backend.auth import hash_password, verify_password

def test_password_hashing():
    pwd = "my_secure_password"
    hashed = hash_password(pwd)
    assert hashed != pwd
    assert len(hashed) > 10

def test_correct_password_verifies():
    pwd = "test_password"
    hashed = hash_password(pwd)
    assert verify_password(pwd, hashed)

def test_wrong_password_rejected():
    pwd = "test_password"
    hashed = hash_password(pwd)
    assert not verify_password("wrong_password", hashed)
