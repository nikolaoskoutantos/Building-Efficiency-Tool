

from fastapi import Depends, HTTPException, status, Request
import jwt
import os
from functools import wraps
from pathlib import Path
from utils.constants import Role

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
        # Accept both string and enum in payload, default to OCCUPANT
        user_role = payload.get("role", str(Role.OCCUPANT))
        try:
            user_role_enum = Role(user_role)
        except ValueError:
            user_role_enum = user_role  # fallback to string if not a valid enum
        if required_roles:
            # Allow required_roles to be enums or strings, convert all to string for comparison
            required_roles_str = [str(r) for r in required_roles]
            if str(user_role_enum) not in required_roles_str:
                raise HTTPException(status_code=403, detail="Insufficient role")
        return payload
    return dependency
