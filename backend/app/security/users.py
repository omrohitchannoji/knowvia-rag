"""
Server-side User Identity and Credential Store.
Enforces that user roles are assigned strictly on the server and verified via credentials,
preventing caller-asserted privilege escalation.
"""

import hashlib
import hmac
import os
from typing import Optional, Dict, Any

# Salt for PBKDF2 hashing (fixed system salt combined with user salt)
SYSTEM_SALT = b"knowvia_system_identity_salt_2026"

def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    """Hashes a password using PBKDF2-HMAC-SHA256."""
    if salt is None:
        salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt + SYSTEM_SALT, iterations=100000)
    return f"{salt.hex()}:{key.hex()}"

def verify_password(plain_password: str, hashed_record: str) -> bool:
    """Verifies a plain password against the stored salt:hash record."""
    try:
        salt_hex, key_hex = hashed_record.split(":")
        salt = bytes.fromhex(salt_hex)
        expected_key = bytes.fromhex(key_hex)
        actual_key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt + SYSTEM_SALT, iterations=100000)
        return hmac.compare_digest(actual_key, expected_key)
    except Exception:
        return False

# Default server-managed user accounts with server-assigned roles.
# Passwords for demo accounts:
#   admin: "AdminPass2026!"
#   internal_analyst: "InternalPass2026!"
#   public_guest: "GuestPass2026!"
USERS_DB: Dict[str, Dict[str, Any]] = {
    "admin": {
        "username": "admin",
        "role": "ADMIN",
        "full_name": "System Administrator",
        "hashed_password": hash_password("AdminPass2026!", salt=b"static_admin_slt"),
        "is_active": True,
    },
    "internal_analyst": {
        "username": "internal_analyst",
        "role": "INTERNAL_USER",
        "full_name": "Internal Knowledge Analyst",
        "hashed_password": hash_password("InternalPass2026!", salt=b"static_int_salt_"),
        "is_active": True,
    },
    "public_guest": {
        "username": "public_guest",
        "role": "PUBLIC_USER",
        "full_name": "Public Guest User",
        "hashed_password": hash_password("GuestPass2026!", salt=b"static_pub_salt_"),
        "is_active": True,
    },
}

def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticates a user against server credentials. Returns user dict or None."""
    user = USERS_DB.get(username.lower().strip())
    if not user:
        return None
    if not user.get("is_active", False):
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return {
        "username": user["username"],
        "role": user["role"],
        "full_name": user["full_name"]
    }
