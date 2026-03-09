from fastapi import Request, HTTPException, status
import jwt
import os

# Constants
JWT_SECRET = os.getenv("SESSION_SECRET_KEY", "your-secret-key")
JWT_ALGORITHM = "HS256"
AUTH_TYPE = os.getenv("AUTH_TYPE", "cookie")

# Error messages
ERROR_NOT_AUTHENTICATED = "Not authenticated"
ERROR_TOKEN_EXPIRED = "Token expired"
ERROR_INVALID_TOKEN = "Invalid token"
BEARER_PREFIX = "Bearer "

def _extract_payload(request: Request) -> dict:
    print(f"[DEBUG] SESSION_SECRET_KEY in auth_dependencies.py: {JWT_SECRET[:10]}...")
    if AUTH_TYPE == "cookie":
        return _extract_cookie_payload(request)
    elif AUTH_TYPE == "jwt":
        return _extract_jwt_payload(request)
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Unsupported AUTH_TYPE: {AUTH_TYPE}",
    )

def _extract_cookie_payload(request: Request) -> dict:
    role = request.session.get("role")
    user_id = request.session.get("user_id")
    if not role or not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_NOT_AUTHENTICATED,
        )
    return {"user_id": user_id, "role": role.upper()}

def _extract_jwt_payload(request: Request) -> dict:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith(BEARER_PREFIX):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_NOT_AUTHENTICATED,
        )
    token = auth_header[len(BEARER_PREFIX):]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_TOKEN_EXPIRED,
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_INVALID_TOKEN,
        )
    user_id = payload.get("user_id") or payload.get("user")
    role = payload.get("role")
    if not user_id or not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_INVALID_TOKEN,
        )
    if role.startswith("Role."):
        role = role[5:]
    return {"user_id": user_id, "role": role.upper()}
def _extract_cookie_payload(request: Request) -> dict:
    role = request.session.get("role")
    user_id = request.session.get("user_id")
    if not role or not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_NOT_AUTHENTICATED,
        )
    return {"user_id": user_id, "role": role.upper()}

def _extract_jwt_payload(request: Request) -> dict:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith(BEARER_PREFIX):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_NOT_AUTHENTICATED,
        )
    token = auth_header[len(BEARER_PREFIX):]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_TOKEN_EXPIRED,
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_INVALID_TOKEN,
        )
    user_id = payload.get("user_id") or payload.get("user")
    role = payload.get("role")
    if not user_id or not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_INVALID_TOKEN,
        )
    if role.startswith("Role."):
        role = role[5:]
    return {"user_id": user_id, "role": role.upper()}
from fastapi import Request, HTTPException, status
import jwt
import os

# Constants
JWT_SECRET = os.getenv("SESSION_SECRET_KEY", "your-secret-key")
JWT_ALGORITHM = "HS256"
AUTH_TYPE = os.getenv("AUTH_TYPE", "cookie")

# Error messages
ERROR_NOT_AUTHENTICATED = "Not authenticated"
ERROR_TOKEN_EXPIRED = "Token expired"
ERROR_INVALID_TOKEN = "Invalid token"
BEARER_PREFIX = "Bearer "


def _extract_payload(request: Request) -> dict:
    """
    Extracts and returns the user payload from either cookie session or JWT,
    depending on AUTH_TYPE. Raises HTTPException on failure.
    """
    print(f"[DEBUG] SESSION_SECRET_KEY in auth_dependencies.py: {JWT_SECRET[:10]}...")
    if AUTH_TYPE == "cookie":
        return _extract_cookie_payload(request)
    elif AUTH_TYPE == "jwt":
        return _extract_jwt_payload(request)
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Unsupported AUTH_TYPE: {AUTH_TYPE}",
    )


def get_current_user_role(allowed_roles: list[str]):
    """
    Dependency factory. Accepts a list of allowed roles (case-insensitive).
    Returns the user payload dict if authorized, raises 403 otherwise.

    Usage:
        user = Depends(get_current_user_role(["ADMIN", "BUILDING_MANAGER"]))
        user_id = user["user_id"]
    """
    # Normalize once at definition time
    normalized_roles = [r.upper() for r in allowed_roles]

    def _check(request: Request) -> dict:
        payload = _extract_payload(request)
        if payload["role"] not in normalized_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access requires one of: {normalized_roles}",
            )
        return payload

    return _check