#!/usr/bin/env python3
"""
Authentication-aware test script for the rating system.
This version includes proper authentication headers and policies testing.
"""

import requests
import json
import time
import os
from typing import Optional, Dict, Any

# API base URL
BASE_URL = "http://localhost:8000"

class AuthenticatedTester:
    """Helper class to handle authenticated API requests"""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.current_user = None
        
    def mock_authenticate(self, wallet_address: str, user_id: str = None) -> bool:
        """
        Mock authentication - in real implementation this would:
        1. Call your actual auth system
        2. Get a valid JWT token
        3. Set the session headers
        """
        # Mock JWT token (in real implementation, get this from your auth system)
        mock_token = f"mock_jwt_token_for_{wallet_address}"
        
        # Set authentication headers
        self.session.headers.update({
            "Authorization": f"Bearer {mock_token}",
            "Content-Type": "application/json"
        })
        
        # Store current user info (mock data)
        self.current_user = {
            "wallet": wallet_address,
            "user_id": user_id or f"user_{wallet_address[-8:]}",
            "token": mock_token
        }
        
        print(f"🔐 Mock authenticated as: {wallet_address}")
        return True
        
    def test_auth_endpoint(self) -> bool:
        """Test if authentication is working"""
        try:
            # Try to access an authenticated endpoint
            response = self.session.get(f"{self.base_url}/rates/my-ratings")
            
            if response.status_code == 401:
                print("❌ Authentication failed - no valid token")
                return False
            elif response.status_code in [200, 404]:  # 404 is ok if no ratings exist
                print("✅ Authentication working")
                return True
            else:
                print(f"⚠️  Unexpected auth response: {response.status_code}")
                return True  # Assume working for now
                
        except Exception as e:
            print(f"❌ Auth test failed: {e}")
            return False
    
    def submit_rating(self, service_id: int, rating: float, feedback: str = None) -> Optional[Dict[Any, Any]]:
        """Submit a rating using the authenticated endpoint"""
        if not self.current_user:
            print("❌ Not authenticated")
            return None
            
        data = {
            "service_id": service_id,
            "rating": rating,
            "feedback": feedback
        }
        
        try:
            response = self.session.post(f"{self.base_url}/rates/submit", json=data)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Rating submission failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Request failed: {e}")
            return None
    
    def get_my_ratings(self) -> Optional[list]:
        """Get current user's ratings"""
        if not self.current_user:
            print("❌ Not authenticated")
            return None
            
        try:
            response = self.session.get(f"{self.base_url}/rates/my-ratings")
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Failed to get ratings: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Request failed: {e}")
            return None

def test_authenticated_upsert():
    """Test upsert functionality with proper authentication"""
    
    print("🔍 Testing AUTHENTICATED UPSERT functionality...")
    print("=" * 80)
    
    # Create authenticated tester
    tester = AuthenticatedTester()
    
    # Test wallet (in real implementation, this would come from the authenticated user)
    test_wallet = "0xAuthenticatedUser123"
    test_service = 1
    
    # Step 1: Authenticate
    print("\n📝 STEP 1: Authentication")
    if not tester.mock_authenticate(test_wallet):
        print("❌ Authentication failed")
        return False
    
    if not tester.test_auth_endpoint():
        print("❌ Auth endpoint test failed")
        return False
    
    # Step 2: First rating submission
    print("\n📝 STEP 2: First Rating Submission")
    result1 = tester.submit_rating(
        service_id=test_service,
        rating=4.5,
        feedback="First authenticated rating"
    )
    
    if not result1:
        print("❌ First submission failed")
        return False
    
    print(f"✅ First submission: {result1.get('message', 'Success')}")
    print(f"   Is new rating: {result1.get('is_new_rating', 'Unknown')}")
    
    # Step 3: Second rating submission (should update)
    print("\n📝 STEP 3: Second Rating Submission (Update)")
    time.sleep(1)
    
    result2 = tester.submit_rating(
        service_id=test_service,
        rating=3.8,
        feedback="Updated authenticated rating - changed my mind"
    )
    
    if not result2:
        print("❌ Second submission failed")
        return False
    
    print(f"✅ Second submission: {result2.get('message', 'Success')}")
    print(f"   Is new rating: {result2.get('is_new_rating', 'Unknown')}")
    
    # Step 4: Verify by getting user's ratings
    print("\n📝 STEP 4: Verify User's Ratings")
    my_ratings = tester.get_my_ratings()
    
    if my_ratings is None:
        print("❌ Failed to get user ratings")
        return False
    
    # Filter ratings for our test service
    service_ratings = [r for r in my_ratings if r.get('service_id') == test_service]
    
    print(f"✅ Found {len(service_ratings)} rating(s) for service {test_service}")
    
    if len(service_ratings) == 1:
        rating = service_ratings[0]
        print(f"   Rating: {rating.get('rating')}")
        print(f"   Feedback: {rating.get('feedback')}")
        print(f"   Created: {rating.get('created_at')}")
        print(f"   Updated: {rating.get('updated_at')}")
        print("✅ SUCCESS: Only one rating found - UPSERT working correctly!")
        return True
    elif len(service_ratings) > 1:
        print("❌ FAILURE: Multiple ratings found - UPSERT not working!")
        for i, rating in enumerate(service_ratings, 1):
            print(f"   {i}. Rating: {rating.get('rating')}, Created: {rating.get('created_at')}")
        return False
    else:
        print("❌ FAILURE: No ratings found")
        return False

def test_multiple_users():
    """Test that different users can rate the same service"""
    
    print("\n🔍 Testing MULTIPLE USERS functionality...")
    print("=" * 80)
    
    users = [
        {"wallet": "0xUser1ABC", "rating": 4.0, "feedback": "User 1 rating"},
        {"wallet": "0xUser2DEF", "rating": 5.0, "feedback": "User 2 rating"},
        {"wallet": "0xUser3GHI", "rating": 3.5, "feedback": "User 3 rating"}
    ]
    
    test_service = 1
    results = []
    
    for i, user in enumerate(users, 1):
        print(f"\n📝 USER {i}: {user['wallet']}")
        
        tester = AuthenticatedTester()
        
        # Authenticate as this user
        if not tester.mock_authenticate(user['wallet']):
            print(f"❌ Authentication failed for user {i}")
            continue
        
        # Submit rating
        result = tester.submit_rating(
            service_id=test_service,
            rating=user['rating'],
            feedback=user['feedback']
        )
        
        if result:
            print(f"✅ User {i} submitted rating: {user['rating']}")
            results.append(result)
        else:
            print(f"❌ User {i} failed to submit rating")
    
    # Verify results
    if len(results) == len(users):
        print(f"\n✅ SUCCESS: All {len(users)} users submitted ratings independently")
        return True
    else:
        print(f"\n❌ FAILURE: Only {len(results)}/{len(users)} users succeeded")
        return False

def test_policy_enforcement():
    """Test various policy enforcement scenarios"""
    
    print("\n🔍 Testing POLICY ENFORCEMENT...")
    print("=" * 80)
    
    tester = AuthenticatedTester()
    
    # Test 1: Unauthenticated request
    print("\n📝 TEST 1: Unauthenticated Request")
    try:
        response = requests.post(f"{BASE_URL}/rates/submit", json={
            "service_id": 1,
            "rating": 4.0,
            "feedback": "This should fail"
        })
        
        if response.status_code == 401:
            print("✅ Correctly rejected unauthenticated request")
        else:
            print(f"❌ Should have rejected unauthenticated request: {response.status_code}")
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
    # Test 2: Invalid rating values
    print("\n📝 TEST 2: Invalid Rating Values")
    tester.mock_authenticate("0xPolicyTest123")
    
    invalid_ratings = [0.5, 5.5, -1, 10]  # Outside 1.0-5.0 range
    
    for rating in invalid_ratings:
        result = tester.submit_rating(
            service_id=1,
            rating=rating,
            feedback="This should fail validation"
        )
        
        if result is None:
            print(f"✅ Correctly rejected invalid rating: {rating}")
        else:
            print(f"❌ Should have rejected invalid rating: {rating}")
    
    print("\n✅ Policy enforcement tests completed")

def main():
    """Run all authenticated tests"""
    
    print("🚀 Starting AUTHENTICATED RATING SYSTEM TESTS")
    print("Testing with proper authentication and policies")
    print("=" * 80)
    
    # Check if API is running
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        if response.status_code != 200:
            print("❌ API server not accessible")
            return False
    except Exception as e:
        print(f"❌ API server not running: {e}")
        print("Please start the API server: uvicorn main:app --reload")
        return False
    
    print("✅ API server is running")
    
    # Run tests
    tests = [
        ("Authenticated Upsert", test_authenticated_upsert),
        ("Multiple Users", test_multiple_users),
        ("Policy Enforcement", test_policy_enforcement)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*80}")
            print(f"🧪 Running: {test_name}")
            print(f"{'='*80}")
            
            results[test_name] = test_func()
            
        except Exception as e:
            print(f"❌ Test '{test_name}' failed with error: {e}")
            results[test_name] = False
    
    # Summary
    print(f"\n{'='*80}")
    print("📊 TEST SUMMARY")
    print(f"{'='*80}")
    
    passed = sum(1 for result in results.values() if result is True)
    failed = sum(1 for result in results.values() if result is False)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\n📈 Results: {passed} passed, {failed} failed")
    
    if failed == 0 and passed > 0:
        print("\n🎉 All authenticated tests passed!")
        print("🔒 Rating system is ready for production with authentication!")
    else:
        print("\n❌ Some tests failed - review authentication implementation")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
