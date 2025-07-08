#!/usr/bin/env python3
"""
Test runner for QoE Application API tests.
Runs all rating system tests in sequence and provides a summary.
"""

import subprocess
import sys
import os
from pathlib import Path

# Get the directory containing this script
TESTS_DIR = Path(__file__).parent

def run_test(test_file):
    """Run a single test file and return success/failure"""
    print(f"\n{'='*80}")
    print(f"🧪 Running {test_file}")
    print(f"{'='*80}")
    
    try:
        result = subprocess.run([
            sys.executable, 
            str(TESTS_DIR / test_file)
        ], capture_output=False, text=True, cwd=TESTS_DIR)
        
        if result.returncode == 0:
            print(f"\n✅ {test_file} - PASSED")
            return True
        else:
            print(f"\n❌ {test_file} - FAILED (exit code: {result.returncode})")
            return False
            
    except Exception as e:
        print(f"\n❌ {test_file} - ERROR: {e}")
        return False

def main():
    """Run all tests and provide summary"""
    print("🚀 QoE Application API Test Suite")
    print("Testing rating system with encrypted wallets and upsert functionality")
    
    # Check if API server is running
    print("\n🔍 Checking prerequisites...")
    
    try:
        import requests
        response = requests.get("http://localhost:8000/docs", timeout=5)
        if response.status_code == 200:
            print("✅ API server is running on http://localhost:8000")
        else:
            print("⚠️  API server responded but may have issues")
    except Exception as e:
        print("❌ API server is not running or not accessible")
        print("   Please start the API server first:")
        print("   cd api && uvicorn main:app --reload")
        return False
    
    # List of tests to run in order
    tests = [
        "test_deterministic_encryption.py",
        "test_upsert.py", 
        "test_complete_system.py"
    ]
    
    results = {}
    
    for test in tests:
        if (TESTS_DIR / test).exists():
            results[test] = run_test(test)
        else:
            print(f"⚠️  Test file {test} not found, skipping...")
            results[test] = None
    
    # Summary
    print(f"\n{'='*80}")
    print("📊 TEST SUMMARY")
    print(f"{'='*80}")
    
    passed = sum(1 for result in results.values() if result is True)
    failed = sum(1 for result in results.values() if result is False)
    skipped = sum(1 for result in results.values() if result is None)
    
    for test, result in results.items():
        if result is True:
            print(f"✅ {test}")
        elif result is False:
            print(f"❌ {test}")
        else:
            print(f"⏭️  {test} (skipped)")
    
    print(f"\n📈 Results: {passed} passed, {failed} failed, {skipped} skipped")
    
    if failed == 0 and passed > 0:
        print("\n🎉 All tests passed! Rating system is working correctly.")
        return True
    else:
        print("\n❌ Some tests failed. Please check the output above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
