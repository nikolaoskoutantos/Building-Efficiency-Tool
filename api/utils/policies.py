from fastapi import Request, HTTPException, status
import jwt
import os

# Constants
JWT_SECRET = os.getenv("SESSION_SECRET_KEY", "your-secret-key")
JWT_ALGORITHM = "HS256"
AUTH_TYPE = os.getenv("AUTH_TYPE", "cookie")

# Error messages
ERROR_NOT_AUTHENTICATED = "Not authenticated"
ERROR_INVALID_TOKEN = "Invalid or expired token"
BEARER_PREFIX = "Bearer "

def require_admin(request: Request):
    if AUTH_TYPE == "cookie":
        role = request.session.get("role")
        if role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    elif AUTH_TYPE == "jwt":
        token = request.headers.get("Authorization")
        if not token or not token.startswith(BEARER_PREFIX):
            raise HTTPException(status_code=401, detail=ERROR_NOT_AUTHENTICATED)
        token = token[7:]
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            if payload.get("role") != "admin":
                raise HTTPException(status_code=403, detail="Admin access required")
        except Exception:
            raise HTTPException(status_code=401, detail=ERROR_INVALID_TOKEN)

def require_building_manager(request: Request):
    if AUTH_TYPE == "cookie":
        role = request.session.get("role")
        if role != "building_manager":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Building manager access required.")
    elif AUTH_TYPE == "jwt":
        token = request.headers.get("Authorization")
        if not token or not token.startswith(BEARER_PREFIX):
            raise HTTPException(status_code=401, detail=ERROR_NOT_AUTHENTICATED)
        token = token[7:]
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            if payload.get("role") != "building_manager":
                raise HTTPException(status_code=403, detail="Building manager access required")
        except Exception:
            raise HTTPException(status_code=401, detail=ERROR_INVALID_TOKEN)

def require_other(request: Request):
    if AUTH_TYPE == "cookie":
        role = request.session.get("role")
        if role != "other":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Other role access required.")
    elif AUTH_TYPE == "jwt":
        token = request.headers.get("Authorization")
        if not token or not token.startswith(BEARER_PREFIX):
            raise HTTPException(status_code=401, detail=ERROR_NOT_AUTHENTICATED)
        token = token[7:]
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            if payload.get("role") != "other":
                raise HTTPException(status_code=403, detail="Other role access required")
        except Exception:
            raise HTTPException(status_code=401, detail=ERROR_INVALID_TOKEN)
