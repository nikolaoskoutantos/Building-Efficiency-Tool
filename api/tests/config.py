# Test Configuration for Rating System
# This file contains configuration for testing the rating system under different scenarios

import os
from typing import Dict, Any, Optional

class TestConfig:
    """Configuration for different testing scenarios"""
    
    # API Configuration
    BASE_URL = os.getenv("TEST_API_URL", "http://localhost:8000")
    
    # Authentication Configuration
    AUTH_TYPE = os.getenv("AUTH_TYPE", "jwt")  # jwt, cookie, none
    
    # Test Users (add your actual test credentials here)
    TEST_USERS = [
        {
            "name": "Test User 1",
            "wallet": "0xTestUser123456789abcdef",
            "token": os.getenv("TEST_USER_1_TOKEN", None),
            "username": os.getenv("TEST_USER_1_USERNAME", "testuser1"),
            "password": os.getenv("TEST_USER_1_PASSWORD", "testpass1")
        },
        {
            "name": "Test User 2", 
            "wallet": "0xTestUser987654321fedcba",
            "token": os.getenv("TEST_USER_2_TOKEN", None),
            "username": os.getenv("TEST_USER_2_USERNAME", "testuser2"),
            "password": os.getenv("TEST_USER_2_PASSWORD", "testpass2")
        }
    ]
    
    # Test Data
    TEST_SERVICES = [
        {"id": 1, "name": "Weather Data Service"},
        {"id": 2, "name": "Environmental Data Service"}
    ]
    
    # Test Scenarios
    SCENARIOS = {
        "upsert_same_service": {
            "description": "Test that multiple ratings for same service update existing record",
            "ratings": [
                {"rating": 4.5, "feedback": "Great service!"},
                {"rating": 3.5, "feedback": "Changed my mind, it's okay"},
                {"rating": 5.0, "feedback": "Actually, it's excellent!"}
            ]
        },
        "different_services": {
            "description": "Test that same user can rate different services",
            "ratings": [
                {"service_id": 1, "rating": 4.0, "feedback": "Good weather service"},
                {"service_id": 2, "rating": 3.0, "feedback": "Okay environmental data"}
            ]
        }
    }
    
    @classmethod
    def get_auth_headers(cls, token: str) -> Dict[str, str]:
        """Get authentication headers based on auth type"""
        if cls.AUTH_TYPE == "jwt":
            return {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        elif cls.AUTH_TYPE == "cookie":
            return {"Content-Type": "application/json"}
        else:
            return {"Content-Type": "application/json"}
    
    @classmethod
    def should_test_authenticated_endpoints(cls) -> bool:
        """Determine if we should test authenticated endpoints"""
        return cls.AUTH_TYPE != "none" and any(
            user.get("token") for user in cls.TEST_USERS
        )
    
    @classmethod
    def get_fallback_test_data(cls) -> Dict[str, Any]:
        """Get test data for fallback (non-authenticated) tests"""
        return {
            "wallet": "0xFallbackTestWallet123",
            "service_id": 1,
            "initial_rating": 4.0,
            "updated_rating": 3.5,
            "initial_feedback": "Initial test rating",
            "updated_feedback": "Updated test rating"
        }

# Environment-specific configurations
class DevelopmentConfig(TestConfig):
    """Configuration for development environment"""
    # Use test endpoints in development
    USE_TEST_ENDPOINTS = True
    STRICT_AUTH = False

class ProductionConfig(TestConfig):
    """Configuration for production environment"""
    # No test endpoints in production
    USE_TEST_ENDPOINTS = False
    STRICT_AUTH = True
    
    # Override base URL for production
    BASE_URL = os.getenv("PROD_API_URL", "https://api.yourapp.com")

class TestingConfig(TestConfig):
    """Configuration for testing environment"""
    USE_TEST_ENDPOINTS = True
    STRICT_AUTH = False
    
    # Use in-memory or test database
    BASE_URL = os.getenv("TEST_API_URL", "http://localhost:8001")

# Select configuration based on environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()

if ENVIRONMENT == "production":
    config = ProductionConfig()
elif ENVIRONMENT == "testing":
    config = TestingConfig()
else:
    config = DevelopmentConfig()

# Export the active configuration
__all__ = ["config", "TestConfig", "DevelopmentConfig", "ProductionConfig", "TestingConfig"]
