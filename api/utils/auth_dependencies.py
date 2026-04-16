from fastapi import HTTPException, Request, WebSocket, status
import jwt
import os
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from sqlalchemy import func

from models.hvac_models import User

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"))

JWT_SECRET = os.getenv("SESSION_SECRET_KEY", "your-secret-key")
JWT_ALGORITHM = "HS256"
# QoE uses JWT auth end-to-end in the app and websocket flows.
AUTH_TYPE = "jwt"

ERROR_NOT_AUTHENTICATED = "Not authenticated"
ERROR_NOT_REGISTERED = "Registered user not found"
ERROR_TOKEN_EXPIRED = "Token expired"
ERROR_INVALID_TOKEN = "Invalid token"
BEARER_PREFIX = "Bearer "


def _normalize_role(role: object) -> str:
    if not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_INVALID_TOKEN,
        )

    normalized_role = str(role)
    if normalized_role.startswith("Role."):
        normalized_role = normalized_role[5:]
    return normalized_role.upper()


def decode_jwt_token(token: str) -> dict:
    if not token or not isinstance(token, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_NOT_AUTHENTICATED,
        )

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

    role = _normalize_role(payload.get("role"))

    return {
        "user_id": payload.get("user_id") or payload.get("user"),
        "wallet": payload.get("wallet"),
        "role": role,
    }


def _extract_payload(request: Request) -> dict:
    if AUTH_TYPE == "cookie":
        return _extract_cookie_payload(request)
    if AUTH_TYPE == "jwt":
        return _extract_jwt_payload(request)
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Unsupported AUTH_TYPE: {AUTH_TYPE}",
    )


def _extract_cookie_payload(request: Request) -> dict:
    role = request.session.get("role")
    user_id = request.session.get("user_id")
    wallet = request.session.get("wallet")
    if not role or (not user_id and not wallet):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_NOT_AUTHENTICATED,
        )
    return {
        "user_id": user_id,
        "wallet": wallet,
        "role": str(role).upper(),
    }


def _extract_jwt_payload(request: Request) -> dict:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith(BEARER_PREFIX):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_NOT_AUTHENTICATED,
        )

    token = auth_header[len(BEARER_PREFIX):]
    return decode_jwt_token(token)


def get_current_user_role(allowed_roles: list[str]):
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


def _extract_cookie_payload_from_websocket(websocket: WebSocket) -> dict:
    session = websocket.scope.get("session") or {}
    role = session.get("role")
    user_id = session.get("user_id")
    wallet = session.get("wallet")
    if not role or (not user_id and not wallet):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_NOT_AUTHENTICATED,
        )
    return {
        "user_id": user_id,
        "wallet": wallet,
        "role": str(role).upper(),
    }


def _extract_jwt_payload_from_websocket(websocket: WebSocket) -> dict:
    auth_header = websocket.headers.get("Authorization")
    token = None

    if auth_header and auth_header.startswith(BEARER_PREFIX):
        token = auth_header[len(BEARER_PREFIX):]
    else:
        token = websocket.query_params.get("token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_NOT_AUTHENTICATED,
        )
    return decode_jwt_token(token)


def get_current_websocket_role(allowed_roles: list[str]):
    normalized_roles = [r.upper() for r in allowed_roles]

    def _check(websocket: WebSocket) -> dict:
        if AUTH_TYPE == "cookie":
            payload = _extract_cookie_payload_from_websocket(websocket)
        elif AUTH_TYPE == "jwt":
            payload = _extract_jwt_payload_from_websocket(websocket)
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unsupported AUTH_TYPE: {AUTH_TYPE}",
            )

        if payload["role"] not in normalized_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access requires one of: {normalized_roles}",
            )
        return payload

    return _check


def resolve_registered_user(payload: dict, db: Session) -> User:
    candidate_user_id = payload.get("user_id")
    wallet = payload.get("wallet")

    if isinstance(candidate_user_id, int):
        user = db.query(User).filter(User.id == candidate_user_id).first()
        if user:
            return user

    if isinstance(candidate_user_id, str) and candidate_user_id.isdigit():
        user = db.query(User).filter(User.id == int(candidate_user_id)).first()
        if user:
            return user

    for wallet_candidate in (wallet, candidate_user_id):
        if isinstance(wallet_candidate, str):
            normalized_wallet = wallet_candidate.strip().lower()
            user = db.query(User).filter(func.lower(User.wallet_address) == normalized_wallet).first()
            if user:
                return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=ERROR_NOT_REGISTERED,
    )


def resolve_registered_user_id(payload: dict, db: Session) -> int:
    return resolve_registered_user(payload, db).id
