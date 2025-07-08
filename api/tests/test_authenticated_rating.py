#!/usr/bin/env python3
"""
Test script for authenticated rating system with policies.
This script tests the real /rates/submit endpoint with proper authentication.
"""

import requests
import json
import time
import os
from typing import Optional, Dict, Any

# API base URL
BASE_URL = "http://localhost:8000"

class AuthenticatedRatingTester:
    """Test class that handles authentication for rating system tests"""
    
    def __init__(self):
        self.auth_headers = {}
        self.current_user_wallet = None
        
    def authenticate_user(self, wallet_address: str, auth_token: Optional[str] = None) -> bool:
        """
        Authenticate a user and set up headers for subsequent requests.
        In a real system, this would call your auth service.
        """
        try:
            # Method 1: Try JWT token if provided
            if auth_token:
                self.auth_headers = {
                    "Authorization": f"Bearer {auth_token}",
                    "Content-Type": "application/json"
                }
                self.current_user_wallet = wallet_address
                return self._verify_auth()
            
            # Method 2: Try session-based auth (simulate login)
            login_data = {
                "wallet_address": wallet_address,
                # Add other required fields based on your auth system
            }
            
            # This would be your actual login endpoint
            response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
            
            if response.status_code == 200:
                result = response.json()
                token = result.get("access_token") or result.get("token")
                if token:
                    self.auth_headers = {
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json"
                    }
                    self.current_user_wallet = wallet_address
                    return True
            
            # Method 3: Try cookie-based auth
            return self._try_cookie_auth(wallet_address)
            
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            return False
    
    def _try_cookie_auth(self, wallet_address: str) -> bool:
        """Try cookie-based authentication"""
        try:
            # Simulate session creation
            session_data = {"wallet": wallet_address}
            response = requests.post(f"{BASE_URL}/auth/session", json=session_data)
            
            if response.status_code == 200:
                # Store cookies for future requests
                self.session = requests.Session()
                self.session.cookies.update(response.cookies)
                self.current_user_wallet = wallet_address
                return True
                
        except Exception:
            pass
        
        return False
    
    def _verify_auth(self) -> bool:
        """Verify that authentication is working"""
        try:
            if hasattr(self, 'session'):
                response = self.session.get(f"{BASE_URL}/rates/my-ratings")
            else:
                response = requests.get(f"{BASE_URL}/rates/my-ratings", headers=self.auth_headers)
            
            # 200 = success, 404 = no ratings (but auth worked)
            return response.status_code in [200, 404]
        except Exception:
            return False
    
    def submit_rating(self, service_id: int, rating: float, feedback: str = None) -> Dict[str, Any]:
        """Submit a rating using authenticated endpoints"""
        data = {
            "service_id": service_id,
            "rating": rating,
            "feedback": feedback
        }
        
        try:
            if hasattr(self, 'session'):
                response = self.session.post(f"{BASE_URL}/rates/submit", json=data)
            else:
                response = requests.post(f"{BASE_URL}/rates/submit", json=data, headers=self.auth_headers)
            
            return {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "data": response.json() if response.status_code == 200 else None,
                "error": response.text if response.status_code != 200 else None
            }
        except Exception as e:
            return {
                "success": False,
                "status_code": 0,
                "error": str(e)
            }
    
    def get_my_ratings(self) -> Dict[str, Any]:
        """Get current user's ratings"""
        try:
            if hasattr(self, 'session'):
                response = self.session.get(f"{BASE_URL}/rates/my-ratings")
            else:
                response = requests.get(f"{BASE_URL}/rates/my-ratings", headers=self.auth_headers)
            
            return {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "data": response.json() if response.status_code == 200 else [],
                "error": response.text if response.status_code != 200 else None
            }
        except Exception as e:
            return {
                "success": False,
                "status_code": 0,
                "error": str(e)
            }

def test_upsert_with_authentication():
    """Test upsert functionality with proper authentication"""
    
    print("🔐 Testing AUTHENTICATED RATING SYSTEM")
    print("=" * 80)
    
    # Test with different authentication methods
    test_users = [
        {
            "wallet": "0xAuthenticatedUser123456",
            "token": None,  # Will try to authenticate
            "name": "User 1"
        },
        # Add more test users as needed
    ]
    
    for user_config in test_users:
        print(f"\n👤 Testing with {user_config['name']} ({user_config['wallet']})")
        
        tester = AuthenticatedRatingTester()
        
        # Try to authenticate
        auth_success = tester.authenticate_user(
            user_config['wallet'], 
            user_config.get('token')
        )
        
        if not auth_success:
            print(f"❌ Authentication failed for {user_config['name']}")
            print("   This is expected if authentication is required")
            continue
        
        print(f"✅ Authentication successful for {user_config['name']}")
        
        # Test upsert functionality
        service_id = 1
        
        # First rating
        print(f"\n📝 FIRST RATING (should INSERT)")
        result1 = tester.submit_rating(service_id, 4.5, "Great service!")
        
        if result1['success']:
            print(f"✅ First rating submitted successfully")
            print(f"   Data: {result1['data']}")
        else:
            print(f"❌ First rating failed: {result1['status_code']} - {result1['error']}")
            continue
        
        time.sleep(1)
        
        # Second rating (should update)
        print(f"\n📝 SECOND RATING (should UPDATE)")
        result2 = tester.submit_rating(service_id, 3.5, "Changed my mind, it's okay")
        
        if result2['success']:
            print(f"✅ Second rating submitted successfully")
            print(f"   Data: {result2['data']}")
            
            # Check if it's an update (same record) or new record
            is_new_1 = result1['data'].get('is_new_rating', True)
            is_new_2 = result2['data'].get('is_new_rating', True)
            
            if is_new_1 and not is_new_2:
                print("✅ UPSERT working: First was INSERT, second was UPDATE")
            elif not is_new_2:
                print("✅ UPSERT working: Second rating updated existing record")
            else:
                print("⚠️  Possible issue: Both ratings appear to be new records")
                
        else:
            print(f"❌ Second rating failed: {result2['status_code']} - {result2['error']}")
        
        # Get user's ratings to verify
        print(f"\n📋 CHECKING USER'S RATINGS")
        ratings_result = tester.get_my_ratings()
        
        if ratings_result['success']:
            ratings = ratings_result['data']
            service_ratings = [r for r in ratings if r['service_id'] == service_id]
            
            print(f"✅ Found {len(service_ratings)} rating(s) for service {service_id}")
            if len(service_ratings) == 1:
                print("✅ Perfect! Only one rating per service (UPSERT working)")
                rating = service_ratings[0]
                print(f"   Final rating: {rating.get('rating')}")
                print(f"   Final feedback: {rating.get('feedback')}")
            elif len(service_ratings) > 1:
                print("❌ Multiple ratings found! UPSERT not working correctly")
                for i, rating in enumerate(service_ratings, 1):
                    print(f"   Rating {i}: {rating.get('rating')} - {rating.get('feedback')}")
            else:
                print("❌ No ratings found! Something went wrong")
        else:
            print(f"❌ Could not retrieve ratings: {ratings_result['error']}")

def test_fallback_to_test_endpoints():
    """Fallback test using test endpoints when auth is not available"""
    
    print("\n🔄 FALLBACK: Testing with non-authenticated endpoints")
    print("=" * 80)
    print("Note: This uses test endpoints and should be removed in production")
    
    # Use the existing test endpoint as fallback
    test_wallet = "0xFallbackTestUser789"
    test_service = 1
    
    print(f"\n📝 Testing with wallet: {test_wallet}")
    
    # First submission
    first_data = {
        "service_id": test_service,
        "wallet_address": test_wallet,
        "rating": 4.0,
        "feedback": "Test rating via fallback"
    }
    
    try:
        response1 = requests.post(f"{BASE_URL}/rates/test-upsert", json=first_data)
        if response1.status_code == 200:
            result1 = response1.json()
            print(f"✅ First submission: {result1.get('action')} - ID: {result1['data']['rate_id']}")
            first_id = result1['data']['rate_id']
        else:
            print(f"❌ First submission failed: {response1.status_code}")
            return
    except Exception as e:
        print(f"❌ First submission error: {e}")
        return
    
    time.sleep(1)
    
    # Second submission
    second_data = {
        "service_id": test_service,
        "wallet_address": test_wallet,
        "rating": 2.5,
        "feedback": "Updated via fallback test"
    }
    
    try:
        response2 = requests.post(f"{BASE_URL}/rates/test-upsert", json=second_data)
        if response2.status_code == 200:
            result2 = response2.json()
            print(f"✅ Second submission: {result2.get('action')} - ID: {result2['data']['rate_id']}")
            second_id = result2['data']['rate_id']
            
            if first_id == second_id:
                print("✅ UPSERT working in fallback mode!")
            else:
                print("❌ UPSERT not working in fallback mode")
        else:
            print(f"❌ Second submission failed: {response2.status_code}")
    except Exception as e:
        print(f"❌ Second submission error: {e}")

def main():
    """Main test function"""
    print("🚀 AUTHENTICATED RATING SYSTEM TEST")
    print("Testing rating system with proper authentication and policies")
    print("=" * 80)
    
    # Check if API is running
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        if response.status_code == 200:
            print("✅ API server is running")
        else:
            print("❌ API server is not responding correctly")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to API server: {e}")
        return False
    
    # Test with authentication
    print("\n🔐 TESTING WITH AUTHENTICATION")
    test_upsert_with_authentication()
    
    # Fallback test
    print("\n🔄 FALLBACK TESTING")
    test_fallback_to_test_endpoints()
    
    print("\n" + "=" * 80)
    print("📋 SUMMARY")
    print("=" * 80)
    print("This test demonstrates how rating system behaves with authentication:")
    print("✅ With proper auth: Uses /rates/submit endpoint")
    print("⚠️  Without auth: Falls back to test endpoints")
    print("🔒 In production: Remove test endpoints and require authentication")
    
    return True

if __name__ == "__main__":
    main()
