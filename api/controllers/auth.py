from fastapi import APIRouter, HTTPException, status, Request, Response, Depends
from pydantic import BaseModel
import os
import requests
import jwt
from datetime import datetime, timedelta

router = APIRouter(prefix="/auth", tags=["Auth"])

AUTH_SYSTEM_URL = os.getenv("AUTH_SYSTEM_URL")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")
JWT_SECRET = os.getenv("SESSION_SECRET_KEY", "your-secret-key")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60
AUTH_TYPE = os.getenv("AUTH_TYPE", "cookie")  # 'cookie' or 'jwt'

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
def login(data: LoginRequest, request: Request, response: Response):
    # Call external auth system
    headers = {"Authorization": f"Bearer {AUTH_TOKEN}"} if AUTH_TOKEN else {}
    try:
        r = requests.post(
            AUTH_SYSTEM_URL,
            json={"username": data.username, "password": data.password},
            headers=headers,
            timeout=10
        )
        r.raise_for_status()
        user_info = r.json()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="External authentication failed")

    # Set session cookie (server-side session) if AUTH_TYPE is cookie
    if AUTH_TYPE == "cookie":
        request.session = {
            "user": user_info.get("username"),
            "role": user_info.get("role"),
            "wallet": user_info.get("wallet")
        }

    # Create JWT token (stateless auth) if AUTH_TYPE is jwt
    token = None
    if AUTH_TYPE == "jwt":
        payload = {
            "user": user_info.get("username"),
            "role": user_info.get("role"),
            "wallet": user_info.get("wallet"),
            "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    response_data = {
        "message": "Login successful",
        "user": user_info.get("username"),
        "role": user_info.get("role"),
        "wallet": user_info.get("wallet")
    }
    if token:
        response_data["token"] = token
    return response_data

@router.post("/logout")
def logout(request: Request):
    request.session = {}
    return {"message": "Logged out"}

@router.get("/me")
def get_me(request: Request, token: str = None):
    # Try session first if AUTH_TYPE is cookie
    if AUTH_TYPE == "cookie":
        user = request.session.get("user")
        role = request.session.get("role")
        wallet = request.session.get("wallet")
        if user:
            return {"user": user, "role": role, "wallet": wallet, "auth_type": "session"}
    # Try JWT if AUTH_TYPE is jwt
    if AUTH_TYPE == "jwt":
        if not token:
            from fastapi import Header
            token = request.headers.get("Authorization")
            if token and token.startswith("Bearer "):
                token = token[7:]
        if token:
            try:
                payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                return {
                    "user": payload.get("user"),
                    "role": payload.get("role"),
                    "wallet": payload.get("wallet"),
                    "auth_type": "jwt"
                }
            except Exception:
                raise HTTPException(status_code=401, detail="Invalid or expired token")
    raise HTTPException(status_code=401, detail="Not authenticated")
