from fastapi import APIRouter

router = APIRouter(prefix="/weather", tags=["Weather"])

@router.get("/ping")
def ping_weather():
    """Simple endpoint to check weather controller is up."""
    return {"message": "Weather controller is ready!"}

# Future endpoints for weather service integration will go here
