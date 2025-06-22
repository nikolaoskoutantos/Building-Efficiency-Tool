from fastapi import APIRouter

router = APIRouter(prefix="/smartcontract", tags=["SmartContract"])

@router.get("/ping")
def ping_smart_contract():
    """Simple endpoint to check smart contract controller is up."""
    return {"message": "Smart contract controller is ready!"}

# Future endpoints for smart contract interaction will go here
