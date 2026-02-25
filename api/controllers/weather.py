from fastapi import APIRouter, Depends
from typing import Annotated
from fastapi import BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import aiohttp
import asyncio

router = APIRouter(prefix="/weather", tags=["Weather"])

@router.get("/ping")
def ping_weather():
    """Simple endpoint to check weather controller is up."""
    return {"message": "Weather controller is ready!"}

