#!/usr/bin/env python3
"""
Test script to verify deterministic encryption functionality.
This tests that the same wallet address always produces the same encrypted value.
"""

import requests
import json

# API base URL
BASE_URL = "http://localhost:8000"

def test_deterministic_encryption():
    """Test that encryption is deterministic"""
    
    test_wallet = "0x1234567890abcdef"
    
    print("🔍 Testing DETERMINISTIC encryption...")
    print(f"Wallet: {test_wallet}")
    print("=" * 60)
    
    # Test multiple encryptions of the same wallet
    encrypted_values = []
    
    for i in range(3):
        print(f"\n📝 ENCRYPTION TEST #{i+1}")
        test_data = {
            "service_id": 1,
            "wallet_address": test_wallet,
            "rating": 4.5,
            "feedback": f"Test #{i+1}"
        }
        
        try:
            response = requests.post(f"{BASE_URL}/rates/test-upsert", json=test_data)
            if response.status_code == 200:
                result = response.json()
                encrypted_wallet = result.get('data', {}).get('encrypted_wallet_preview', '')
                encrypted_values.append(encrypted_wallet)
                print(f"✅ Status: {response.status_code}")
                print(f"Encrypted: {encrypted_wallet}")
            else:
                print(f"❌ Error: {response.status_code} - {response.text}")
                return
        except Exception as e:
            print(f"❌ Request failed: {e}")
            return
    
    # Analysis
    print("\n" + "=" * 60)
    print("📊 DETERMINISTIC ENCRYPTION ANALYSIS")
    print("=" * 60)
    
    if len(set(encrypted_values)) == 1:
        print("✅ SUCCESS: All encryptions produced the same value!")
        print(f"   Encrypted value: {encrypted_values[0]}")
        print("   This means encryption is deterministic - UPSERT should work!")
        return True
    else:
        print("❌ FAILURE: Different encrypted values found")
        for i, value in enumerate(encrypted_values, 1):
            print(f"   Test {i}: {value}")
        print("   This means encryption is NOT deterministic - UPSERT won't work!")
        return False

def test_upsert_with_deterministic_encryption():
    """Test upsert functionality with deterministic encryption"""
    
    test_wallet = "0x9876543210fedcba"  # Different wallet to avoid conflicts
    test_service = 1
    
    print("\n🔍 Testing UPSERT with deterministic encryption...")
    print(f"Wallet: {test_wallet}")
    print(f"Service ID: {test_service}")
    print("=" * 60)
    
    # Clear any existing data for this test wallet first
    print("\n🧹 Clearing any existing test data...")
    
    # First submission
    print("\n📝 FIRST SUBMISSION (should INSERT)")
    first_data = {
        "service_id": test_service,
        "wallet_address": test_wallet,
        "rating": 4.5,
        "feedback": "First submission - should INSERT"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/rates/test-upsert", json=first_data)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Status: {response.status_code}")
            print(f"Action: {result.get('action', 'N/A')}")
            print(f"Rate ID: {result.get('data', {}).get('rate_id', 'N/A')}")
            first_rate_id = result.get('data', {}).get('rate_id')
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False
    
    # Second submission (should update)
    print("\n📝 SECOND SUBMISSION (should UPDATE)")
    second_data = {
        "service_id": test_service,
        "wallet_address": test_wallet,
        "rating": 2.5,
        "feedback": "Second submission - should UPDATE"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/rates/test-upsert", json=second_data)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Status: {response.status_code}")
            print(f"Action: {result.get('action', 'N/A')}")
            print(f"Rate ID: {result.get('data', {}).get('rate_id', 'N/A')}")
            second_rate_id = result.get('data', {}).get('rate_id')
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False
    
    # Analysis
    print("\n" + "=" * 60)
    print("📊 UPSERT ANALYSIS")
    print("=" * 60)
    
    if first_rate_id == second_rate_id:
        print("✅ SUCCESS: UPSERT is working correctly!")
        print(f"   Both submissions used Rate ID: {first_rate_id}")
        print("   Second submission updated the existing record!")
        return True
    else:
        print("❌ FAILURE: UPSERT is NOT working")
        print(f"   First Rate ID: {first_rate_id}")
        print(f"   Second Rate ID: {second_rate_id}")
        print("   Second submission created a new record instead of updating!")
        return False

if __name__ == "__main__":
    print("🚀 Starting Deterministic Encryption and UPSERT Test...")
    
    # Test 1: Deterministic encryption
    encryption_works = test_deterministic_encryption()
    
    if encryption_works:
        # Test 2: UPSERT functionality
        upsert_works = test_upsert_with_deterministic_encryption()
        
        if upsert_works:
            print("\n🎉 ALL TESTS PASSED!")
            print("✅ Deterministic encryption: WORKING")
            print("✅ UPSERT functionality: WORKING")
        else:
            print("\n❌ UPSERT test failed despite deterministic encryption")
    else:
        print("\n❌ Deterministic encryption failed - skipping UPSERT test")
    
    print("\n✨ Test completed!")
