from fastapi import APIRouter, HTTPException, status, Request, Response, Depends
from typing import Annotated
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import os
import requests
import jwt
from datetime import datetime, timedelta, timezone
from eth_account.messages import encode_defunct
from eth_account import Account
import hashlib
import logging
from utils.rate_limit import rate_limit_dependency
from db.connection import SessionLocal
from models.hvac_models import User, UserBuilding
from db.connection import get_db
from models.hvac_unit import HVACUnit
import bcrypt
from utils.constants import Role

router = APIRouter(tags=["Device & User Authentication"])

# Device authentication request/response schemas
class DeviceAuthRequest(BaseModel):
    device_key: str
    device_secret: str


# Standard device auth response
class DeviceAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

# EMQX-compatible response
class EMQXAuthResponse(BaseModel):
    result: str
    is_superuser: Optional[bool] = None

# --- Device Authentication (JWT issuing for devices) ---


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
    x_request_source = request.headers.get("x-request-source")
    hvac_unit = db.query(HVACUnit).filter(HVACUnit.device_key == req.device_key).first()
    if x_request_source and x_request_source.upper() == "EMQX":
        if not hvac_unit or hvac_unit.device_revoked_at:
            return JSONResponse(content={"result": "deny"})
        if not hvac_unit.device_secret_hash or not bcrypt.checkpw(req.device_secret.encode(), hvac_unit.device_secret_hash.encode()):
            return JSONResponse(content={"result": "deny"})
        return JSONResponse(content={"result": "allow", "is_superuser": False})

    # Standard device authentication (JWT issuing)
    if not hvac_unit:
        raise HTTPException(status_code=404, detail="Device not found.")
    if hvac_unit.device_revoked_at:
        raise HTTPException(status_code=401, detail="Device credentials revoked.")
    if not hvac_unit.device_secret_hash or not bcrypt.checkpw(req.device_secret.encode(), hvac_unit.device_secret_hash.encode()):
        raise HTTPException(status_code=401, detail="Invalid device credentials.")
    payload = {
        "sub": str(hvac_unit.id),
        "typ": Role.DEVICE,
        "building_id": hvac_unit.building_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return DeviceAuthResponse(access_token=token)


# Configure logging
logger = logging.getLogger("auth")
logging.basicConfig(level=logging.INFO)

AUTH_SYSTEM_URL = os.getenv("AUTH_SYSTEM_URL")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")
JWT_SECRET = os.environ.get("SESSION_SECRET_KEY")
if not JWT_SECRET:
    raise RuntimeError("SESSION_SECRET_KEY must be set in your .env file or environment variables for JWT authentication.")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60
AUTH_TYPE = os.getenv("AUTH_TYPE", "cookie")  # 'cookie' or 'jwt'

class LoginRequest(BaseModel):
    # Traditional login fields (optional)
    username: Optional[str] = None
    password: Optional[str] = None
    # Web3 login fields (optional)
    message: Optional[str] = None
    signature: Optional[str] = None
    nonce: Optional[str] = None
    address: Optional[str] = None


def get_db():
    db_session = SessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()

DbSession = Annotated[Session, Depends(get_db)]

@router.post(
    "/login",
    responses={
        400: {"description": "Invalid login request. Provide either username/password or Web3 signature data."},
        401: {"description": "Unauthorized: Invalid credentials or signature."},
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
            return handle_traditional_login(data, request)
        else:
            raise HTTPException(
                status_code=400, 
                detail="Invalid login request. Provide either username/password or Web3 signature data."
            )
    except HTTPException as e:
        logger.warning("Login failed", extra={"detail": str(e.detail).replace('\n', ' ').replace('\r', ' ')})
        raise
    except Exception as e:
        logger.error("Unexpected error during login", extra={"error": str(e).replace('\n', ' ').replace('\r', ' ')})
        raise HTTPException(status_code=500, detail="Internal server error during login")

def handle_traditional_login(data: LoginRequest, request: Request):
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
    logger.info(f"Traditional login successful for user {user_info.get('username')}")
    return create_auth_response(
        user=user_info.get("username"),
        role=user_info.get("role", "user"),
        wallet=user_info.get("wallet"),
        auth_method="traditional",
        request=request
    )

def handle_web3_login(data: LoginRequest, request: Request, db_session: Session):
    """Handle Web3 signature-based login."""
    try:
        # Validate message format
        if not validate_message_format(data.message, data.address, data.nonce):
            logger.warning(
                "Invalid message format for wallet",
                extra={"wallet": str(data.address).replace('\n', ' ').replace('\r', ' ')}
            )
            raise HTTPException(
                status_code=400, 
                detail="Invalid message format"
            )

        # Verify the signature
        if not verify_ethereum_signature(data.message, data.signature, data.address):
            logger.warning(
                "Invalid signature for wallet",
                extra={"wallet": str(data.address).replace('\n', ' ').replace('\r', ' ')}
            )
            raise HTTPException(
                status_code=401, 
                detail="Invalid signature"
            )

        # Look up the user's role from the DB using db_session
        user = db_session.query(User).filter(User.wallet_address == data.address).first()
        if not user:
            logger.warning(
                "Wallet not registered",
                extra={"wallet": str(data.address).replace('\n', ' ').replace('\r', ' ')}
            )
            raise HTTPException(status_code=401, detail="Wallet not registered")
        # Find all active roles for this user (across all buildings)
        user_roles = db_session.query(UserBuilding).filter(
            UserBuilding.user_id == user.id,
            UserBuilding.status == "active"
        ).all()
        if not user_roles:
            role = Role.OCCUPANT
        else:
            # If multiple, pick the most privileged (admin > owner > manager > occupant > device > user)
            role_priority = {
                Role.ADMIN: 4,
                Role.BUILDING_MANAGER: 3,  # If you want to treat building_manager as manager
                Role.OCCUPANT: 2,
                Role.DEVICE: 1,
                Role.USER if hasattr(Role, 'USER') else "user": 0
            }
            # Map DB role string to enum if possible
            def map_role(r):
                try:
                    return Role(r)
                except ValueError:
                    return r
            role = max((map_role(ur.role) for ur in user_roles), key=lambda r: role_priority.get(r, 0))

        logger.info(
            "Web3 login successful for wallet with role",
            extra={
                "wallet": str(data.address).replace('\n', ' ').replace('\r', ' '),
                "role": str(role).replace('\n', ' ').replace('\r', ' ')
            }
        )
        # Create session/token for Web3 user with correct role
        return create_auth_response(
            user=data.address,
            role=role,
            wallet=data.address,
            auth_method="web3",
            request=request
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
        logger.error(
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

def create_auth_response(user: str, role: str, wallet: str, auth_method: str, request: Request):
    """Create unified authentication response with session/JWT."""
    print(f"🔧 AUTH_TYPE: {AUTH_TYPE}")
    print(f"🔧 JWT_SECRET: {JWT_SECRET[:10]}...")
    print(f"🔧 Creating auth response for user: {user}")
    
    # Set session cookie (server-side session) if AUTH_TYPE is cookie
    if AUTH_TYPE == "cookie":
        print("🍪 Setting session cookie...")
        request.session.update({
            "user": user,
            "role": str(role),
            "wallet": wallet,
            "auth_method": auth_method,
            "verified_at": datetime.now(timezone.utc).isoformat()
        })

    # Create JWT token (stateless auth) if AUTH_TYPE is jwt
    token = None
    if AUTH_TYPE == "jwt":
        print("🔑 Creating JWT token...")
        # Support multiple roles if present (role can be a list or string)
        payload = {
            "user": user,
            "role": str(role) if isinstance(role, Role) else role,
            "wallet": wallet,
            "auth_method": auth_method,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        print(f"✅ JWT token created: {token[:20]}...")

    response_data = {
        "success": True,
        "message": "Login successful",
        "user": user,
        "role": role,
        "wallet": wallet,
        "auth_method": auth_method
    }
    
    if token:
        response_data["token"] = token
        print("Returning response with JWT token")
    else:
        print("Returning response without JWT token")
        
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
        print(f"Signature verification error: {e}")
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
def logout(request: Request):
    """
    Logout endpoint that handles both traditional and Web3 sessions.
    """
    # Clear session
    request.session.clear()
    return {"message": "Logged out successfully"}

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
        role = request.session.get("role", str(Role.OCCUPANT))
        wallet = request.session.get("wallet")
        auth_method = request.session.get("auth_method", "traditional")
        
        if user:
            return {
                "user": user,
                "role": role,
                "wallet": wallet,
                "auth_method": auth_method,
                "auth_type": "session"
            }
    
    # Try JWT if AUTH_TYPE is jwt
    if AUTH_TYPE == "jwt":
        token = request.headers.get("Authorization")
        if token and token.startswith("Bearer "):
            token = token[7:]
            try:
                payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                return {
                    "user": payload.get("user"),
                    "role": payload.get("role", str(Role.OCCUPANT)),
                    "wallet": payload.get("wallet"),
                    "auth_method": payload.get("auth_method", "traditional"),
                    "auth_type": "jwt"
                }
            except Exception:
                pass
    
    raise HTTPException(status_code=401, detail="Not authenticated")
