"""
Database module - redirects to the new db package structure.
This file maintains backward compatibility for existing imports.
"""

# Import everything from the new db package
from db.connection import engine, SessionLocal, Base, get_db

# Re-export for backward compatibility
__all__ = ["engine", "SessionLocal", "Base", "get_db"]
