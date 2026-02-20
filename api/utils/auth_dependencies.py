
from fastapi import Depends, HTTPException, status, Request
import jwt
import os
from functools import wraps
from pathlib import Path

# Load .env if present
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
except ImportError:
    pass

JWT_SECRET = os.environ.get("SESSION_SECRET_KEY")
if not JWT_SECRET:
    raise RuntimeError("SESSION_SECRET_KEY must be set in your .env file or environment variables for JWT authentication.")
JWT_ALGORITHM = "HS256"

# Dependency to extract and verify JWT, and check role
def get_current_user_role(required_roles=None):
    def dependency(request: Request):
        token = request.headers.get("Authorization")
        if not token or not token.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
        token = token[7:]
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        user_role = payload.get("role", "user")
        if required_roles and user_role not in required_roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return payload
    return dependency
