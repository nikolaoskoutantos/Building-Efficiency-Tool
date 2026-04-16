"""
Database connection configuration.
Main database connection file - replaces the old api/db.py
"""


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../.env'))

# Database URL configuration - now using PostgreSQL
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
if not SQLALCHEMY_DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set. Please define it in your .env file as DATABASE_URL=postgresql://user:password@host:port/dbname"
    )


engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Define async DB helpers when asyncpg is available. This keeps sync-only scripts
# usable even in lighter local environments.
async_engine = None
async_session_maker = None
try:
    if SQLALCHEMY_DATABASE_URL.startswith("postgresql+asyncpg"):
        async_url = SQLALCHEMY_DATABASE_URL
    else:
        async_url = SQLALCHEMY_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    async_engine = create_async_engine(async_url)
    async_session_maker = async_sessionmaker(async_engine, expire_on_commit=False)
except ModuleNotFoundError as exc:
    if exc.name != "asyncpg":
        raise

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class
Base = declarative_base()

def get_db():
    """
    Dependency to get database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
