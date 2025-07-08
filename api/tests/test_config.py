#!/usr/bin/env python3
"""
Test configuration for different environments and scenarios.
"""

import os
from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class TestConfig:
    """Configuration for test scenarios"""
    api_base_url: str
    use_authentication: bool
    auth_type: str  # 'jwt', 'cookie', 'mock'
    test_endpoints: bool  # Whether to use test endpoints or production endpoints
    auth_token: Optional[str] = None
    mock_users: Dict[str, Any] = None

# Different test configurations
CONFIGS = {
    "development_no_auth": TestConfig(
        api_base_url="http://localhost:8000",
        use_authentication=False,
        auth_type="mock",
        test_endpoints=True,
        mock_users={
            "user1": {"wallet": "0x1234567890abcdef", "token": "mock_token_1"},
            "user2": {"wallet": "0x9876543210fedcba", "token": "mock_token_2"},
            "user3": {"wallet": "0xabcdef1234567890", "token": "mock_token_3"}
        }
    ),
    
    "development_with_auth": TestConfig(
        api_base_url="http://localhost:8000",
        use_authentication=True,
        auth_type="jwt",
        test_endpoints=False,  # Use production endpoints
        auth_token=os.getenv("TEST_AUTH_TOKEN"),
        mock_users={
            "user1": {"wallet": "0x1234567890abcdef", "user_id": "test_user_1"},
            "user2": {"wallet": "0x9876543210fedcba", "user_id": "test_user_2"},
            "user3": {"wallet": "0xabcdef1234567890", "user_id": "test_user_3"}
        }
    ),
    
    "staging": TestConfig(
        api_base_url="https://staging-api.yourapp.com",
        use_authentication=True,
        auth_type="jwt",
        test_endpoints=False,
        auth_token=os.getenv("STAGING_AUTH_TOKEN")
    ),
    
    "production": TestConfig(
        api_base_url="https://api.yourapp.com",
        use_authentication=True,
        auth_type="jwt",
        test_endpoints=False,
        auth_token=os.getenv("PROD_AUTH_TOKEN")
    )
}

def get_config(env: str = None) -> TestConfig:
    """Get test configuration for specified environment"""
    if env is None:
        env = os.getenv("TEST_ENV", "development_no_auth")
    
    if env not in CONFIGS:
        raise ValueError(f"Unknown test environment: {env}. Available: {list(CONFIGS.keys())}")
    
    return CONFIGS[env]

def validate_config(config: TestConfig) -> bool:
    """Validate that configuration is complete"""
    if config.use_authentication and config.auth_type == "jwt" and not config.auth_token:
        print(f"❌ Authentication required but no auth token provided")
        print(f"   Set TEST_AUTH_TOKEN environment variable")
        return False
    
    return True

# Example environment variables you might need:
"""
# For development with authentication
export TEST_ENV=development_with_auth
export TEST_AUTH_TOKEN=your_dev_jwt_token

# For staging
export TEST_ENV=staging
export STAGING_AUTH_TOKEN=your_staging_jwt_token

# For production (be careful!)
export TEST_ENV=production
export PROD_AUTH_TOKEN=your_prod_jwt_token
"""
