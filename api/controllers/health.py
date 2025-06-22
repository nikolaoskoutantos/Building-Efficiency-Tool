from fastapi import APIRouter
from datetime import datetime, timezone

router = APIRouter()

@router.get("/health", tags=["Health"])
def read_root():
    return {
        "message": "FastAPI server is running!",
        "utc_timestamp": datetime.now(timezone.utc).isoformat()
    }
