#!/usr/bin/env python3
"""
Test script to verify upsert functionality for the rating system.
This script will test if submitting multiple ratings with the same wallet and service
results in updates (not duplicates).
"""

import requests
import json
import time

# API base URL
BASE_URL = "http://localhost:8000"

def test_upsert_functionality():
    """Test the upsert endpoint with multiple submissions"""
    
    # Test data - same wallet and service
    test_wallet = "0x1234567890abcdef"
    test_service = 1
    
    print("🔍 Testing UPSERT functionality...")
    print(f"Wallet: {test_wallet}")
    print(f"Service ID: {test_service}")
    print("=" * 60)
    
    # First submission
    print("\n📝 FIRST SUBMISSION (should INSERT)")
    first_data = {
        "service_id": test_service,
        "wallet_address": test_wallet,
        "rating": 4.5,
        "feedback": "First rating - should be inserted"
    }
    
    try:
        response1 = requests.post(f"{BASE_URL}/rates/test-upsert", json=first_data)
        if response1.status_code == 200:
            result1 = response1.json()
            print(f"✅ Status: {response1.status_code}")
            print(f"Action: {result1.get('action', 'N/A')}")
            print(f"Rate ID: {result1.get('data', {}).get('rate_id', 'N/A')}")
            print(f"Rating: {result1.get('data', {}).get('rating', 'N/A')}")
            print(f"Message: {result1.get('message', 'N/A')}")
            first_rate_id = result1.get('data', {}).get('rate_id')
        else:
            print(f"❌ Error: {response1.status_code} - {response1.text}")
            return
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return
    
    # Wait a moment
    time.sleep(1)
    
    # Second submission (should update)
    print("\n📝 SECOND SUBMISSION (should UPDATE)")
    second_data = {
        "service_id": test_service,
        "wallet_address": test_wallet,
        "rating": 3.0,
        "feedback": "Updated rating - should update existing record"
    }
    
    try:
        response2 = requests.post(f"{BASE_URL}/rates/test-upsert", json=second_data)
        if response2.status_code == 200:
            result2 = response2.json()
            print(f"✅ Status: {response2.status_code}")
            print(f"Action: {result2.get('action', 'N/A')}")
            print(f"Rate ID: {result2.get('data', {}).get('rate_id', 'N/A')}")
            print(f"Rating: {result2.get('data', {}).get('rating', 'N/A')}")
            print(f"Message: {result2.get('message', 'N/A')}")
            second_rate_id = result2.get('data', {}).get('rate_id')
        else:
            print(f"❌ Error: {response2.status_code} - {response2.text}")
            return
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return
    
    # Third submission (should also update)
    time.sleep(1)
    print("\n📝 THIRD SUBMISSION (should also UPDATE)")
    third_data = {
        "service_id": test_service,
        "wallet_address": test_wallet,
        "rating": 5.0,
        "feedback": "Final rating - should update existing record again"
    }
    
    try:
        response3 = requests.post(f"{BASE_URL}/rates/test-upsert", json=third_data)
        if response3.status_code == 200:
            result3 = response3.json()
            print(f"✅ Status: {response3.status_code}")
            print(f"Action: {result3.get('action', 'N/A')}")
            print(f"Rate ID: {result3.get('data', {}).get('rate_id', 'N/A')}")
            print(f"Rating: {result3.get('data', {}).get('rating', 'N/A')}")
            print(f"Message: {result3.get('message', 'N/A')}")
            third_rate_id = result3.get('data', {}).get('rate_id')
        else:
            print(f"❌ Error: {response3.status_code} - {response3.text}")
            return
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return
    
    # Analysis
    print("\n" + "=" * 60)
    print("📊 ANALYSIS")
    print("=" * 60)
    
    if first_rate_id and second_rate_id and third_rate_id:
        if first_rate_id == second_rate_id == third_rate_id:
            print("✅ SUCCESS: All submissions used the same rate ID")
            print(f"   Rate ID: {first_rate_id}")
            print("   This means UPSERT is working correctly!")
        else:
            print("❌ FAILURE: Different rate IDs found")
            print(f"   First ID: {first_rate_id}")
            print(f"   Second ID: {second_rate_id}")
            print(f"   Third ID: {third_rate_id}")
            print("   This means UPSERT is NOT working - creating duplicates!")
    
    # Test with different service (should create new record)
    print("\n📝 TESTING DIFFERENT SERVICE (should INSERT)")
    different_service_data = {
        "service_id": 2,  # Different service
        "wallet_address": test_wallet,  # Same wallet
        "rating": 2.5,
        "feedback": "Rating for different service - should be new record"
    }
    
    try:
        response4 = requests.post(f"{BASE_URL}/rates/test-upsert", json=different_service_data)
        if response4.status_code == 200:
            result4 = response4.json()
            print(f"✅ Status: {response4.status_code}")
            print(f"Action: {result4.get('action', 'N/A')}")
            print(f"Rate ID: {result4.get('data', {}).get('rate_id', 'N/A')}")
            fourth_rate_id = result4.get('data', {}).get('rate_id')
            
            if fourth_rate_id != first_rate_id:
                print("✅ Correct: Different service created new record")
            else:
                print("❌ Error: Same rate ID for different service")
        else:
            print(f"❌ Error: {response4.status_code} - {response4.text}")
    except Exception as e:
        print(f"❌ Request failed: {e}")

def view_current_data():
    """View current encrypted data in the database"""
    print("\n" + "=" * 60)
    print("👀 CURRENT DATABASE CONTENT")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/rates/test-view-data")
        if response.status_code == 200:
            result = response.json()
            data = result.get('data', [])
            print(f"Found {len(data)} records:")
            
            for i, record in enumerate(data, 1):
                print(f"\n{i}. Rate ID: {record.get('rate_id')}")
                print(f"   Service: {record.get('service_id')} ({record.get('service_name', 'Unknown')})")
                print(f"   Rating: {record.get('rating')}")
                print(f"   Feedback: {record.get('feedback', 'None')}")
                print(f"   Wallet Preview: {record.get('encrypted_wallet_preview', 'N/A')}")
                print(f"   Created: {record.get('created_at', 'N/A')}")
        else:
            print(f"❌ Error fetching data: {response.status_code}")
    except Exception as e:
        print(f"❌ Failed to fetch data: {e}")

if __name__ == "__main__":
    print("🚀 Starting UPSERT Test...")
    
    # First show current state
    view_current_data()
    
    # Test upsert functionality
    test_upsert_functionality()
    
    # Show final state
    view_current_data()
    
    print("\n✨ Test completed!")
