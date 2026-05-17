from fastapi import APIRouter, HTTPException, status, Request, Response, Depends
from typing import Annotated
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field, AliasChoices
from typing import Optional
import os
import requests
import jwt
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from eth_account.messages import encode_defunct
from eth_account import Account
import logging
from utils.rate_limit import rate_limit_dependency, web3_register_rate_limit_dependency
from models.hvac_models import User, UserBuilding, Building
from models.device_token import DeviceToken
from db.connection import get_db
from models.hvac_unit import HVACUnit
import bcrypt
from utils.constants import Role
from utils.token_service import (
    issue_token_pair,
    verify_refresh_token,
    revoke_token,
    revoke_all_user_tokens,
    ACCESS_TOKEN_MINUTES,
    REFRESH_TOKEN_DAYS,
)
from utils.audit import (
    log_event, log_event_commit, get_client_ip,
    EVENT_LOGIN_SUCCESS, EVENT_LOGIN_FAILURE,
    EVENT_LOGOUT, EVENT_LOGOUT_ALL,
    EVENT_REFRESH_SUCCESS, EVENT_REFRESH_FAILURE,
    EVENT_TOKEN_REUSE, EVENT_NONCE_REJECTED,
)

# Device JWT constants (separate from user token service)
JWT_SECRET = os.environ.get("SESSION_SECRET_KEY")
if not JWT_SECRET:
    raise RuntimeError("SESSION_SECRET_KEY must be set in your .env file or environment variables.")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.environ.get("DEVICE_JWT_EXPIRE_MINUTES", "30"))
_BEARER_PREFIX = "Bearer "

router = APIRouter(tags=["Device & User Authentication"])

# Device authentication request/response schemas
class DeviceAuthRequest(BaseModel):
    # Accepts both device_key/device_secret (REST) and username/password (EMQX HTTP auth plugin)
    device_key: str = Field(validation_alias=AliasChoices("device_key", "username"))
    device_secret: str = Field(validation_alias=AliasChoices("device_secret", "password"))


# Standard device auth response
class DeviceAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

# EMQX-compatible response
class EMQXAuthResponse(BaseModel):
    result: str
    is_superuser: Optional[bool] = None

# --- Device Authentication (JWT issuing for devices) ---


def _is_emqx_request(request: Request) -> bool:
    x_request_source = request.headers.get("x-request-source")
    return bool(x_request_source and x_request_source.upper() == "EMQX")


def _is_valid_service_user(req: DeviceAuthRequest) -> bool:
    service_user = os.environ.get("MQTT_SERVICE_USER", "")
    service_pass = os.environ.get("MQTT_SERVICE_PASS", "")
    return bool(
        service_user
        and service_pass
        and req.device_key == service_user
        and req.device_secret == service_pass
    )


def _verify_device_secret(hvac_unit: HVACUnit, device_secret: str) -> bool:
    return bool(
        hvac_unit.device_secret_hash
        and bcrypt.checkpw(device_secret.encode(), hvac_unit.device_secret_hash.encode())
    )


def _build_device_auth_response(hvac_unit: HVACUnit, db: Session) -> DeviceAuthResponse:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    token_jti = str(uuid.uuid4())
    cfp = hashlib.sha256(hvac_unit.device_secret_hash.encode()).hexdigest()[:16]
    payload = {
        "sub": str(hvac_unit.id),
        "typ": Role.DEVICE,
        "building_id": hvac_unit.building_id,
        "cfp": cfp,
        "jti": token_jti,
        "exp": expires_at,
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    db.add(DeviceToken(
        jti=token_jti,
        hvac_unit_id=hvac_unit.id,
        expires_at=expires_at,
    ))
    db.commit()
    return DeviceAuthResponse(access_token=token)


from fastapi.responses import JSONResponse

@router.post(
    "/device/auth",
    responses={
        200: {"description": "Device authenticated", "content": {"application/json": {}}},
        401: {"description": "Invalid device credentials or revoked."},
        404: {"description": "Device not found."},
        500: {"description": "Internal server error."}
    },
    tags=["Device & User Authentication"]
)
def device_auth(
    req: DeviceAuthRequest,
    db: Annotated[Session, Depends(get_db)],
    request: Request
):
    if _is_emqx_request(request) and _is_valid_service_user(req):
        return JSONResponse(content={"result": "allow", "is_superuser": False})

    hvac_unit = db.query(HVACUnit).filter(HVACUnit.device_key == req.device_key).first()
    if _is_emqx_request(request):
        if not hvac_unit or hvac_unit.device_revoked_at:
            return JSONResponse(content={"result": "deny"})
        if not _verify_device_secret(hvac_unit, req.device_secret):
            return JSONResponse(content={"result": "deny"})
        return JSONResponse(content={"result": "allow", "is_superuser": False})

    if not hvac_unit:
        raise HTTPException(status_code=404, detail="Device not found.")
    if hvac_unit.device_revoked_at:
        raise HTTPException(status_code=401, detail="Device credentials revoked.")
    if not _verify_device_secret(hvac_unit, req.device_secret):
        raise HTTPException(status_code=401, detail="Invalid device credentials.")
    return _build_device_auth_response(hvac_unit, db)


# Configure logging
logger = logging.getLogger("auth")
logging.basicConfig(level=logging.INFO)

AUTH_SYSTEM_URL = os.getenv("AUTH_SYSTEM_URL")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")
# QoE uses JWT auth end-to-end in the app and websocket flows.
AUTH_TYPE = "jwt"

class LoginRequest(BaseModel):
    # Traditional login fields (optional)
    username: Optional[str] = None
    password: Optional[str] = None
    # Web3 login fields (optional)
    message: Optional[str] = None
    signature: Optional[str] = None
    nonce: Optional[str] = None
    address: Optional[str] = None


class RegisterRequest(BaseModel):
    wallet_address: str

    # Option 1: Map to existing building
    building_id: Optional[int] = None

    # Option 2: Create new building and map
    building_name: Optional[str] = None
    building_address: Optional[str] = None
    building_lat: Optional[str] = None
    building_lon: Optional[str] = None
    building_metadata: Optional[str] = None

    # User role for the mapping
    role: Optional[str] = "occupant"


class Web3RegisterRequest(BaseModel):
    address: str
    message: str
    signature: str
    nonce: str
    captcha_token: Optional[str] = None
    building_name: str
    building_address: Optional[str] = None
    building_lat: str
    building_lon: str
    building_metadata: Optional[str] = None
    role: Optional[str] = "occupant"


class RegisterResponse(BaseModel):
    success: bool
    message: str
    user_id: Optional[int] = None
    building_id: Optional[int] = None
    building_created: Optional[bool] = False


def normalize_wallet_address(wallet_address: Optional[str]) -> Optional[str]:
    if not wallet_address:
        return wallet_address
    return wallet_address.strip().lower()


def _verify_turnstile_token(token: Optional[str], remote_ip: Optional[str]) -> bool:
    secret = os.getenv("TURNSTILE_SECRET_KEY")
    if not secret:
        logger.warning("TURNSTILE_SECRET_KEY not configured; captcha verification skipped")
        return True

    if not token:
        return False

    try:
        response = requests.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data={
                "secret": secret,
                "response": token,
                "remoteip": remote_ip or "",
            },
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        return bool(payload.get("success"))
    except Exception as exc:
        logger.warning(
            "Captcha verification failed",
            extra={"error": str(exc).replace('\n', ' ').replace('\r', ' ')},
        )
        return False


def _is_localhost_request(request: Request) -> bool:
    hostname = (request.url.hostname or "").lower()
    if hostname in {"localhost", "127.0.0.1", "::1"}:
        return True

    origin = (request.headers.get("origin") or "").lower()
    referer = (request.headers.get("referer") or "").lower()
    localhost_markers = ("http://localhost", "https://localhost", "http://127.0.0.1", "https://127.0.0.1")

    return any(marker in origin or marker in referer for marker in localhost_markers)


def _validate_captcha_or_raise(token: Optional[str], request: Request) -> None:
    if _is_localhost_request(request):
        logger.info("Skipping captcha verification for localhost request")
        return
    if not _verify_turnstile_token(token, get_client_ip(request)):
        raise HTTPException(status_code=400, detail="Captcha verification failed")


DbSession = Annotated[Session, Depends(get_db)]

@router.post(
    "/login",
    responses={
        400: {"description": "Invalid login request. Provide either username/password or Web3 signature data."},
        401: {"description": "Unauthorized: Invalid credentials or signature."},
        403: {"description": "No active building access. Registration may still be pending approval."},
        500: {"description": "Internal server error during login"}
    }
)
def login(
    data: LoginRequest,
    request: Request,
    response: Response,
    rate_limit: Annotated[None, Depends(rate_limit_dependency)],
    db_session: DbSession
):
    """
    Unified login endpoint that handles both traditional and Web3 authentication.
    """
    try:
        # Check if this is Web3 authentication
        if data.address and data.signature and data.message and data.nonce:
            return handle_web3_login(data, request, db_session)
        # Check if this is traditional authentication
        elif data.username and data.password:
            return handle_traditional_login(data, request, db_session)
        else:
            raise HTTPException(
                status_code=400, 
                detail="Invalid login request. Provide either username/password or Web3 signature data."
            )
    except HTTPException as e:
        logger.warning("Login failed", extra={"detail": str(e.detail).replace('\n', ' ').replace('\r', ' ')})
        raise
    except Exception as e:
        logger.exception("Unexpected error during login", extra={"error": str(e).replace('\n', ' ').replace('\r', ' ')})
        raise HTTPException(status_code=500, detail="Internal server error during login")

def handle_traditional_login(data: LoginRequest, request: Request, db_session: Session):
    """Handle traditional username/password login."""
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
        logger.warning(
            "External authentication failed for user", 
            extra={
                "username": str(data.username).replace('\n', ' ').replace('\r', ' '),
                "error": str(e).replace('\n', ' ').replace('\r', ' ')
            }
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="External authentication failed")

    # Create session/token
    logger.info("Traditional login successful")
    wallet = normalize_wallet_address(user_info.get("wallet"))
    user = (
        db_session.query(User)
        .filter(func.lower(User.wallet_address) == wallet)
        .first()
        if wallet
        else None
    )
    return create_auth_response(
        user=user_info.get("username"),
        role=user_info.get("role", "user"),
        wallet=wallet,
        auth_method="traditional",
        request=request,
        user_id=user.id if user else None,
        db=db_session,
    )

def handle_web3_login(data: LoginRequest, request: Request, db_session: Session):
    """Handle Web3 signature-based login."""
    try:
        normalized_address = normalize_wallet_address(data.address)
        _validate_web3_message(data)
        _validate_web3_signature(data)
        user = _get_web3_user_or_raise(normalized_address, db_session)
        _validate_web3_nonce_freshness(data.nonce, user, db_session, request)
        role = _resolve_web3_role(user.id, db_session)

        logger.info(
            "Web3 login successful for wallet with role",
            extra={
                "wallet": str(data.address).replace('\n', ' ').replace('\r', ' '),
                "normalized_wallet": str(normalized_address).replace('\n', ' ').replace('\r', ' '),
                "role": str(role).replace('\n', ' ').replace('\r', ' ')
            }
        )
        # Create session/token for Web3 user with correct role
        return create_auth_response(
            user=normalized_address,
            role=role,
            wallet=normalized_address,
            auth_method="web3",
            request=request,
            user_id=user.id,
            db=db_session,
        )

    except HTTPException as e:
        logger.warning(
            "Web3 login failed for wallet",
            extra={
                "wallet": str(data.address).replace('\n', ' ').replace('\r', ' '),
                "detail": str(e.detail).replace('\n', ' ').replace('\r', ' ')
            }
        )
        raise
    except Exception as e:
        logger.exception(
            "Web3 login error for wallet",
            extra={
                "wallet": str(data.address).replace('\n', ' ').replace('\r', ' '),
                "error": str(e).replace('\n', ' ').replace('\r', ' ')
            }
        )
        raise HTTPException(
            status_code=500, 
            detail="Internal server error during Web3 authentication"
        )


def _validate_web3_message(data: LoginRequest) -> None:
    if validate_message_format(data.message, data.address, data.nonce):
        return

    logger.warning(
        "Invalid message format for wallet",
        extra={"wallet": str(data.address).replace('\n', ' ').replace('\r', ' ')}
    )
    raise HTTPException(status_code=400, detail="Invalid message format")


def _validate_web3_signature(data: LoginRequest) -> None:
    if verify_ethereum_signature(data.message, data.signature, data.address):
        return

    logger.warning(
        "Invalid signature for wallet",
        extra={"wallet": str(data.address).replace('\n', ' ').replace('\r', ' ')}
    )
    raise HTTPException(status_code=401, detail="Invalid signature")


# ---------------------------------------------------------------------------
# Web3 nonce replay protection
# ---------------------------------------------------------------------------

# Maximum age of a Web3 nonce in seconds (5 minutes).
_NONCE_MAX_AGE_S = 300


def _validate_web3_nonce_freshness(
    nonce: str, user: User, db_session: Session, request: Request
) -> None:
    """Reject stale or replayed Web3 nonces.

    Nonce format expected from the UI: "<uuid>:<unix_timestamp_ms>"
    Legacy format (plain UUID, no timestamp): timestamp check is skipped;
    only the monotonic last_nonce_ts check is applied.

    Steps:
    1. Parse the timestamp from the nonce (if present).
    2. Reject if the timestamp is older than _NONCE_MAX_AGE_S.
    3. Reject if timestamp <= user.last_nonce_ts (replay of an old session).
    4. On success, update user.last_nonce_ts to the current timestamp.
    """
    nonce_ts: Optional[int] = None

    if nonce and ":" in nonce:
        parts = nonce.rsplit(":", 1)
        try:
            nonce_ts = int(parts[1])
        except (ValueError, IndexError):
            logger.warning("Unparseable nonce timestamp")  # nosonar

    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    if nonce_ts is not None:
        age_s = (now_ms - nonce_ts) / 1000
        if age_s > _NONCE_MAX_AGE_S:
            log_event_commit(
                db_session,
                event_type=EVENT_NONCE_REJECTED,
                success=False,
                user_id=user.id,
                ip_address=get_client_ip(request),
                details={"reason": "stale", "age_s": age_s},
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Nonce expired — please sign a fresh message",
            )
        if age_s < -120:
            # Future timestamp > 2 minutes — likely clock skew or tampering
            log_event_commit(
                db_session,
                event_type=EVENT_NONCE_REJECTED,
                success=False,
                user_id=user.id,
                ip_address=get_client_ip(request),
                details={"reason": "future_timestamp", "age_s": age_s},
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Nonce timestamp is in the future",
            )

    # Monotonic replay check: reject any nonce whose timestamp is <= the last
    # successfully used one, regardless of the 5-minute window.
    last = user.last_nonce_ts  # may be None for new accounts
    if last is not None and nonce_ts is not None and nonce_ts <= last:
        log_event_commit(
            db_session,
            event_type=EVENT_NONCE_REJECTED,
            success=False,
            user_id=user.id,
            ip_address=get_client_ip(request),
            details={"reason": "replay", "nonce_ts": nonce_ts, "last_nonce_ts": last},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nonce already used — please sign a fresh message",
        )

    # Advance the monotonic counter.
    if nonce_ts is not None:
        user.last_nonce_ts = nonce_ts
        db_session.flush()





def _get_web3_user_or_raise(normalized_address: str, db_session: Session) -> User:
    user = (
        db_session.query(User)
        .filter(func.lower(User.wallet_address) == normalized_address)
        .first()
    )
    if user:
        return user

    logger.warning(
        "Wallet not registered",
        extra={"wallet": str(normalized_address).replace('\n', ' ').replace('\r', ' ')}
    )
    raise HTTPException(status_code=401, detail="Wallet not registered")


def _map_role_value(role_value):
    try:
        return Role(role_value)
    except ValueError:
        return role_value


def _resolve_web3_role(user_id: int, db_session: Session):
    user_roles = db_session.query(UserBuilding).filter(
        UserBuilding.user_id == user_id,
        UserBuilding.status == "active"
    ).all()
    if not user_roles:
        raise HTTPException(
            status_code=403,
            detail="No active building access. Registration may still be pending approval."
        )

    role_priority = {
        Role.ADMIN: 4,
        Role.BUILDING_MANAGER: 3,
        Role.OCCUPANT: 2,
        Role.DEVICE: 1,
        Role.USER if hasattr(Role, "USER") else "user": 0,
    }
    return max((_map_role_value(user_role.role) for user_role in user_roles), key=lambda role: role_priority.get(role, 0))

def create_auth_response(
    user: str,
    role: str,
    wallet: str,
    auth_method: str,
    request: Request,
    user_id: Optional[int] = None,
    db: Optional[Session] = None,
):
    """Create unified authentication response with session/JWT.

    When AUTH_TYPE is 'jwt' and a db session is provided, tokens are issued
    via token_service (jti tracked, revocable).  Without a db session the
    legacy single-token path is used as a fallback (backward compat for
    call sites that haven't been updated yet).
    """
    # Set session cookie (server-side session) if AUTH_TYPE is cookie
    if AUTH_TYPE == "cookie":
        request.session.update({
            "user": user,
            "user_id": user_id,
            "role": str(role),
            "wallet": wallet,
            "auth_method": auth_method,
            "verified_at": datetime.now(timezone.utc).isoformat()
        })

    access_token = None
    refresh_token = None

    if AUTH_TYPE == "jwt":
        role_str = str(role) if isinstance(role, Role) else role
        if db is not None and user_id is not None:
            # Secure path: tracked tokens with jti + revocation support
            access_token, refresh_token = issue_token_pair(
                user_id=user_id,
                role=role_str,
                wallet=wallet,
                db=db,
            )
        else:
            # Legacy fallback: single token without jti (no DB available)
            payload = {
                "user": user,
                "user_id": user_id,
                "role": role_str,
                "wallet": wallet,
                "auth_method": auth_method,
                "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_MINUTES),
            }
            access_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    response_data = {
        "success": True,
        "message": "Login successful",
        "user": user,
        "user_id": user_id,
        "role": role,
        "wallet": wallet,
        "auth_method": auth_method,
        "token_lifetime_minutes": ACCESS_TOKEN_MINUTES,
    }

    if access_token:
        response_data["token"] = access_token
    if refresh_token:
        response_data["refresh_token"] = refresh_token

    return response_data


# ===============================
# Web3 Authentication Endpoints  
# ===============================

def verify_ethereum_signature(message: str, signature: str, expected_address: str) -> bool:
    """
    Verify that a message was signed by the expected Ethereum address.
    """
    try:
        # Create the message hash that was signed
        message_hash = encode_defunct(text=message)
        
        # Recover the address from the signature
        recovered_address = Account.recover_message(message_hash, signature=signature)
        
        # Compare addresses (case-insensitive)
        return recovered_address.lower() == expected_address.lower()
    except Exception as e:
        logger.warning("Signature verification error", extra={"error": str(e).replace('\n', ' ').replace('\r', ' ')})
        return False

def validate_message_format(message: str, address: str, nonce: str) -> bool:
    """
    Validate that the message contains the expected format and content.
    """
    try:
        # Check if message contains required components
        required_components = [
            "Welcome to QoE Application!",
            "Click to sign in and accept the Terms of Service.",
            "This request will not trigger a blockchain transaction or cost any gas fees.",
            f"Wallet address: {address}",
            f"Nonce: {nonce}",
            "Issued at:"
        ]
        
        for component in required_components:
            if component not in message:
                return False
        
        return True
    except Exception:
        return False

@router.post(
    "/logout",
    responses={
        200: {"description": "Logged out successfully"},
        401: {"description": "Not authenticated"},
        500: {"description": "Internal server error during logout"}
    }
)
def logout(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
):
    """Revoke the current access token (and its paired refresh token if provided).

    For JWT mode: extracts jti from the Bearer token and marks it revoked in
    user_tokens.  The refresh token can optionally be passed in the request
    body to revoke it as well.
    For cookie mode: clears the server-side session.
    """
    user_id: Optional[int] = None
    jti: Optional[str] = None

    if AUTH_TYPE == "jwt":
        auth = request.headers.get("Authorization", "")
        if auth.startswith(_BEARER_PREFIX):
            token = auth[len(_BEARER_PREFIX):]
            try:
                payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                jti = payload.get("jti")
                user_id = payload.get("user_id")
            except Exception:
                pass
        if jti:
            revoke_token(jti, db)

    request.session.clear()

    log_event_commit(
        db,
        event_type=EVENT_LOGOUT,
        success=True,
        user_id=user_id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
        details={"jti": jti},
    )
    return {"message": "Logged out successfully"}


@router.post(
    "/logout-all",
    responses={
        200: {"description": "All sessions revoked"},
        401: {"description": "Not authenticated"},
    }
)
def logout_all(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
):
    """Revoke ALL active tokens for the authenticated user.

    Use this when a device is lost/stolen or after a suspected compromise.
    """
    user_id: Optional[int] = None

    if AUTH_TYPE == "jwt":
        auth = request.headers.get("Authorization", "")
        if auth.startswith(_BEARER_PREFIX):
            token = auth[len(_BEARER_PREFIX):]
            try:
                payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                user_id = payload.get("user_id")
            except Exception:
                pass

    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    count = revoke_all_user_tokens(int(user_id), db)
    request.session.clear()

    log_event_commit(
        db,
        event_type=EVENT_LOGOUT_ALL,
        success=True,
        user_id=int(user_id),
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
        details={"revoked_count": count},
    )
    return {"message": f"All sessions revoked ({count} token(s) invalidated)"}


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post(
    "/refresh",
    responses={
        200: {"description": "New token pair issued"},
        401: {"description": "Invalid, expired, or revoked refresh token"},
    }
)
def refresh_tokens(
    body: RefreshRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
):
    """Rotate refresh token — issue a new access + refresh token pair.

    Security behaviour:
    - Validates the refresh JWT signature and expiry.
    - Checks the jti exists in user_tokens and is not revoked.
    - If the token IS already revoked (reuse detected): immediately revokes ALL
      active tokens for that user and returns 401 (token-theft response).
    - Otherwise: marks old refresh token as revoked (replaced_by_jti set),
      issues new access + refresh pair, returns both.
    """
    try:
        payload, old_record = verify_refresh_token(body.refresh_token, db)
    except HTTPException as exc:
        # Token-theft path: verify_refresh_token already called revoke_all.
        log_event_commit(
            db,
            event_type=EVENT_TOKEN_REUSE if "reuse" in exc.detail else EVENT_REFRESH_FAILURE,
            success=False,
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent"),
            details={"detail": exc.detail},
        )
        raise

    user_id = int(payload["user_id"])

    # Look up current role from the DB (role may have changed since last login)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    from utils.token_service import _now as _ts_now
    from models.user_token import UserToken as _UT

    # Resolve current role
    role_str = payload.get("role", "OCCUPANT")  # keep role from refresh token
    wallet = payload.get("wallet")

    # Issue new pair
    new_access, new_refresh = issue_token_pair(
        user_id=user_id,
        role=role_str,
        wallet=wallet,
        db=db,
    )

    # Decode new access jti to record the replaced_by_jti link
    new_refresh_payload = jwt.decode(new_refresh, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    new_refresh_jti = new_refresh_payload.get("jti")

    # Revoke old refresh token, record successor jti
    old_record.revoked_at = datetime.now(timezone.utc)
    old_record.replaced_by_jti = new_refresh_jti
    db.commit()

    log_event_commit(
        db,
        event_type=EVENT_REFRESH_SUCCESS,
        success=True,
        user_id=user_id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
        details={"old_jti": old_record.jti, "new_refresh_jti": new_refresh_jti},
    )

    return {
        "token": new_access,
        "refresh_token": new_refresh,
        "token_lifetime_minutes": ACCESS_TOKEN_MINUTES,
        "refresh_lifetime_days": REFRESH_TOKEN_DAYS,
    }



@router.get(
    "/me",
    responses={
        200: {"description": "Current user information returned"},
        401: {"description": "Not authenticated"},
        500: {"description": "Internal server error during authentication check"}
    }
)
def get_current_user(request: Request):
    """
    Get current user endpoint that handles both traditional and Web3 authentication.
    """
    # Try session first if AUTH_TYPE is cookie
    if AUTH_TYPE == "cookie":
        user = request.session.get("user")
        user_id = request.session.get("user_id")
        role = request.session.get("role", str(Role.OCCUPANT))
        wallet = request.session.get("wallet")
        auth_method = request.session.get("auth_method", "traditional")
        
        if user:
            return {
                "user": user,
                "user_id": user_id,
                "role": role,
                "wallet": wallet,
                "auth_method": auth_method,
                "auth_type": "session"
            }
    
    # Try JWT if AUTH_TYPE is jwt
    if AUTH_TYPE == "jwt":
        token = request.headers.get("Authorization")
        if token and token.startswith(_BEARER_PREFIX):
            token = token[len(_BEARER_PREFIX):]
            try:
                payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                return {
                    "user": payload.get("user"),
                    "user_id": payload.get("user_id"),
                    "role": payload.get("role", str(Role.OCCUPANT)),
                    "wallet": payload.get("wallet"),
                    "auth_method": payload.get("auth_method", "traditional"),
                    "auth_type": "jwt"
                }
            except Exception:
                pass
    
    raise HTTPException(status_code=401, detail="Not authenticated")


# Helper functions to reduce cognitive complexity
def _validate_registration_request(data: RegisterRequest) -> None:
    """Validate registration request data."""
    data.wallet_address = normalize_wallet_address(data.wallet_address)
    # Validate wallet address format
    if not data.wallet_address.startswith("0x") or len(data.wallet_address) != 42:
        raise HTTPException(
            status_code=400, 
            detail="Invalid wallet address format. Must be 42-character hex string starting with '0x'"
        )
    
    # Validate that either building_id OR building creation fields are provided
    if data.building_id is None and not data.building_name:
        raise HTTPException(
            status_code=400,
            detail="Either 'building_id' (existing building) or 'building_name' (new building) must be provided"
        )
    
    if data.building_id is not None and data.building_name:
        raise HTTPException(
            status_code=400,
            detail="Provide either 'building_id' OR building creation fields, not both"
        )
    
    # Validate role
    valid_roles = ["occupant", "building_manager", "admin", "device", "user"]
    if data.role not in valid_roles:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}"
        )


def _validate_web3_registration_request(data: Web3RegisterRequest) -> None:
    normalized_address = normalize_wallet_address(data.address)
    if not normalized_address or not normalized_address.startswith("0x") or len(normalized_address) != 42:
        raise HTTPException(
            status_code=400,
            detail="Invalid wallet address format. Must be 42-character hex string starting with '0x'",
        )

    valid_roles = ["occupant", "building_manager", "admin", "device", "user"]
    if data.role not in valid_roles:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}",
        )

    try:
        lat = float(data.building_lat)
        lon = float(data.building_lon)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Building latitude/longitude must be numeric")

    if not (-90 <= lat <= 90):
        raise HTTPException(status_code=400, detail="Building latitude must be between -90 and 90")
    if not (-180 <= lon <= 180):
        raise HTTPException(status_code=400, detail="Building longitude must be between -180 and 180")

def _resolve_or_create_building(data: RegisterRequest, db_session: Session) -> tuple[Building, bool]:
    """Resolve existing building or create new one. Returns (building, was_created)."""
    # Case 1: Map to existing building
    building_id = getattr(data, "building_id", None)
    if building_id is not None:
        building = db_session.query(Building).filter(Building.id == building_id).first()
        if not building:
            raise HTTPException(
                status_code=400,
                detail=f"Building with ID {building_id} not found"
            )
        logger.info("Using existing building", extra={"building_id": building.id})
        return building, False

    # Case 2: Create new building
    building_did = f"0x{hashlib.sha256(data.building_name.encode()).hexdigest()[:10]}"
    
    # Check if building with same DID already exists
    existing_building = db_session.query(Building).filter(Building.did == building_did).first()
    if existing_building:
        raise HTTPException(
            status_code=400,
            detail=f"Building with DID {building_did} already exists"
        )
    
    # Create new building
    building = Building(
        did=building_did,
        name=data.building_name,
        address=data.building_address or "",
        lat=data.building_lat or "0.0",
        lon=data.building_lon or "0.0",
        building_metadata=getattr(data, "building_metadata", None),
    )
    db_session.add(building)
    db_session.commit()
    db_session.refresh(building)
    logger.info("Created new building", extra={"building_id": building.id})
    return building, True

def _resolve_or_create_user(wallet_address: str, db_session: Session) -> User:
    """Resolve existing user or create new one."""
    wallet_address = normalize_wallet_address(wallet_address)
    user = db_session.query(User).filter(func.lower(User.wallet_address) == wallet_address).first()
    if user:
        if user.wallet_address != wallet_address:
            user.wallet_address = wallet_address
            db_session.commit()
            db_session.refresh(user)
        logger.info("Existing user resolved", extra={"user_id": user.id})
        return user

    # Create new user
    user = User(wallet_address=wallet_address)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    logger.info("New user created", extra={"user_id": user.id})
    return user

def _handle_user_building_mapping(
    user: User, building: Building, role: str, building_created: bool, db_session: Session
) -> RegisterResponse:
    """Handle user-building mapping logic."""
    # Check if user-building mapping already exists
    existing_mapping = db_session.query(UserBuilding).filter(
        UserBuilding.user_id == user.id,
        UserBuilding.building_id == building.id
    ).first()
    
    if existing_mapping:
        if existing_mapping.status == "active":
            return RegisterResponse(
                success=False,
                message=f"User is already registered for building {building.id} ({building.name}) with role '{existing_mapping.role}'",
                user_id=user.id,
                building_id=building.id,
                building_created=building_created
            )
        else:
            # Reactivate existing mapping
            existing_mapping.status = "active"
            existing_mapping.role = role
            db_session.commit()
            return RegisterResponse(
                success=True,
                message=f"Successfully reactivated user registration for building {building.id} ({building.name}) with role '{role}'",
                user_id=user.id,
                building_id=building.id,
                building_created=building_created
            )
    else:
        # Create new user-building mapping
        user_building = UserBuilding(
            user_id=user.id,
            building_id=building.id,
            role=role,
            status="active"
        )
        db_session.add(user_building)
        db_session.commit()
        
        success_message = f"Successfully registered wallet {user.wallet_address} for building {building.id} ({building.name}) with role '{role}'"
        if building_created:
            success_message += " (new building created)"
            
        return RegisterResponse(
            success=True,
            message=success_message,
            user_id=user.id,
            building_id=building.id,
            building_created=building_created
        )


def _handle_pending_user_building_mapping(
    user: User, building: Building, role: str, building_created: bool, db_session: Session
) -> RegisterResponse:
    existing_mapping = db_session.query(UserBuilding).filter(
        UserBuilding.user_id == user.id,
        UserBuilding.building_id == building.id
    ).first()

    if existing_mapping:
        if existing_mapping.status == "active":
            return RegisterResponse(
                success=False,
                message=f"User is already registered for building {building.id} ({building.name}) with role '{existing_mapping.role}'",
                user_id=user.id,
                building_id=building.id,
                building_created=building_created
            )

        if existing_mapping.status == "pending":
            return RegisterResponse(
                success=False,
                message=f"Registration request is already pending approval for {building.name}",
                user_id=user.id,
                building_id=building.id,
                building_created=building_created
            )

        existing_mapping.status = "pending"
        existing_mapping.role = role
        db_session.commit()
        return RegisterResponse(
            success=True,
            message=f"Registration request is pending approval for {building.name}",
            user_id=user.id,
            building_id=building.id,
            building_created=building_created
        )

    db_session.add(UserBuilding(
        user_id=user.id,
        building_id=building.id,
        role=role,
        status="pending"
    ))
    db_session.commit()

    success_message = f"Registration request submitted for {building.name}"
    if building_created:
        success_message += " (new building created)"

    return RegisterResponse(
        success=True,
        message=success_message,
        user_id=user.id,
        building_id=building.id,
        building_created=building_created
    )


@router.post(
    "/register-web3",
    responses={
        200: {"description": "Registration request submitted"},
        400: {"description": "Invalid request or captcha verification failed"},
        401: {"description": "Invalid wallet signature"},
        409: {"description": "User is already registered for this building"},
        500: {"description": "Internal server error during registration"}
    },
    tags=["Device & User Authentication"]
)
def register_web3_user(
    data: Web3RegisterRequest,
    request: Request,
    rate_limit: Annotated[None, Depends(web3_register_rate_limit_dependency)],
    db_session: DbSession
) -> RegisterResponse:
    try:
        _validate_web3_registration_request(data)
        _validate_captcha_or_raise(data.captcha_token, request)
        normalized_address = normalize_wallet_address(data.address)

        if not validate_message_format(data.message, data.address, data.nonce):
            raise HTTPException(status_code=400, detail="Invalid message format")
        if not verify_ethereum_signature(data.message, data.signature, data.address):
            raise HTTPException(status_code=401, detail="Invalid signature")

        building, building_created = _resolve_or_create_building(data, db_session)
        user = db_session.query(User).filter(func.lower(User.wallet_address) == normalized_address).first()

        if user:
            if user.wallet_address != normalized_address:
                user.wallet_address = normalized_address
                db_session.commit()
                db_session.refresh(user)
        else:
            user = User(wallet_address=normalized_address, status="pending")
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

        return _handle_pending_user_building_mapping(
            user=user,
            building=building,
            role=data.role or "occupant",
            building_created=building_created,
            db_session=db_session
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Web3 registration error", extra={"error": str(e).replace('\n', ' ').replace('\r', ' ')})
        db_session.rollback()
        raise HTTPException(
            status_code=500,
            detail="Internal server error during registration"
        )

@router.post(
    "/register",
    responses={
        200: {"description": "User registered successfully"},
        400: {"description": "Invalid request data or building not found"},
        409: {"description": "User already registered for this building"},
        500: {"description": "Internal server error during registration"}
    },
    tags=["Device & User Authentication"]
)
def register_user(
    data: RegisterRequest,
    db_session: DbSession
) -> RegisterResponse:
    """
    Register a wallet address to a building with a specified role.
    Can either map to existing building or create new building.
    
    Args:
        data: Registration request containing wallet_address and either:
              - building_id (to map to existing building), OR
              - building creation fields (to create new building and map)
        
    Returns:
        RegisterResponse with success status and details
    """
    try:
        _validate_registration_request(data)
        building, building_created = _resolve_or_create_building(data, db_session)
        user = _resolve_or_create_user(data.wallet_address, db_session)
        return _handle_user_building_mapping(user, building, data.role, building_created, db_session)
            
    except HTTPException as e:
        logger.warning("Registration failed", extra={"detail": str(e.detail).replace('\n', ' ').replace('\r', ' ')})
        raise
    except Exception as e:
        logger.exception("Registration error", extra={"error": str(e).replace('\n', ' ').replace('\r', ' ')})
        db_session.rollback()
        raise HTTPException(
            status_code=500,
            detail="Internal server error during registration"
        )
