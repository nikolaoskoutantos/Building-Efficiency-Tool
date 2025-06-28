from fastapi import APIRouter, HTTPException, status, Request, Response, Depends
from pydantic import BaseModel
import os
import requests
import jwt
from datetime import datetime, timedelta
from eth_account.messages import encode_defunct
from eth_account import Account
import hashlib

router = APIRouter(prefix="/auth", tags=["Auth"])

AUTH_SYSTEM_URL = os.getenv("AUTH_SYSTEM_URL")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")
JWT_SECRET = os.getenv("SESSION_SECRET_KEY", "your-secret-key")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60
AUTH_TYPE = os.getenv("AUTH_TYPE", "cookie")  # 'cookie' or 'jwt'

class LoginRequest(BaseModel):
    # Traditional login fields (optional)
    username: str = None
    password: str = None
    
    # Web3 login fields (optional)
    message: str = None
    signature: str = None
    nonce: str = None
    address: str = None

@router.post("/login")
def login(data: LoginRequest, request: Request, response: Response):
    """
    Unified login endpoint that handles both traditional and Web3 authentication.
    """
    # Check if this is Web3 authentication
    if data.address and data.signature and data.message and data.nonce:
        return handle_web3_login(data, request)
    
    # Check if this is traditional authentication
    elif data.username and data.password:
        return handle_traditional_login(data, request)
    
    else:
        raise HTTPException(
            status_code=400, 
            detail="Invalid login request. Provide either username/password or Web3 signature data."
        )

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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="External authentication failed")

    # Create session/token
    return create_auth_response(
        user=user_info.get("username"),
        role=user_info.get("role", "user"),
        wallet=user_info.get("wallet"),
        auth_method="traditional",
        request=request
    )

def handle_web3_login(data: LoginRequest, request: Request):
    """Handle Web3 signature-based login."""
    try:
        # Validate message format
        if not validate_message_format(data.message, data.address, data.nonce):
            raise HTTPException(
                status_code=400, 
                detail="Invalid message format"
            )
        
        # Verify the signature
        if not verify_ethereum_signature(data.message, data.signature, data.address):
            raise HTTPException(
                status_code=401, 
                detail="Invalid signature"
            )
        
        # Create session/token for Web3 user
        return create_auth_response(
            user=data.address,
            role="user",
            wallet=data.address,
            auth_method="web3",
            request=request
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Web3 login error: {e}")
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
            "role": role,
            "wallet": wallet,
            "auth_method": auth_method,
            "verified_at": datetime.utcnow().isoformat()
        })

    # Create JWT token (stateless auth) if AUTH_TYPE is jwt
    token = None
    if AUTH_TYPE == "jwt":
        print("🔑 Creating JWT token...")
        payload = {
            "user": user,
            "role": role,
            "wallet": wallet,
            "auth_method": auth_method,
            "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
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
        print(f"📤 Returning response with JWT token")
    else:
        print(f"📤 Returning response without JWT token")
        
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

@router.post("/logout")
def logout(request: Request):
    """
    Logout endpoint that handles both traditional and Web3 sessions.
    """
    # Clear session
    request.session.clear()
    return {"message": "Logged out successfully"}

@router.get("/me")
def get_current_user(request: Request):
    """
    Get current user endpoint that handles both traditional and Web3 authentication.
    """
    # Try session first if AUTH_TYPE is cookie
    if AUTH_TYPE == "cookie":
        user = request.session.get("user")
        role = request.session.get("role", "user")
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
                    "role": payload.get("role", "user"),
                    "wallet": payload.get("wallet"),
                    "auth_method": payload.get("auth_method", "traditional"),
                    "auth_type": "jwt"
                }
            except Exception:
                pass
    
    raise HTTPException(status_code=401, detail="Not authenticated")
