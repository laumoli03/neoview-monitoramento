#!/usr/bin/env python3
"""
NeoView Glucose Monitor API Test Suite
Tests all backend endpoints with comprehensive validation
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any

class NeoViewAPITester:
    def __init__(self, base_url="https://6f9bb811-3e2d-4e46-8362-3ead774bf09e.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name: str, success: bool, details: str = ""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {details}")
        
        self.test_results.append({
            "name": name,
            "success": success,
            "details": details
        })

    def test_root_endpoint(self):
        """Test root endpoint"""
        try:
            response = requests.get(f"{self.base_url}/")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                details += f", Message: {data.get('message', 'No message')}"
            self.log_test("Root Endpoint", success, details)
            return success
        except Exception as e:
            self.log_test("Root Endpoint", False, str(e))
            return False

    def test_post_glucose_reading(self, glucose_value: float, device_id: str = "Test_ESP32"):
        """Test POST /api/glucose endpoint"""
        try:
            payload = {
                "glucose_value": glucose_value,
                "device_id": device_id
            }
            
            response = requests.post(
                f"{self.base_url}/api/glucose",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                data = response.json()
                # Validate response structure
                required_fields = ["id", "glucose_value", "category", "timestamp", "device_id", "color"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    success = False
                    details += f", Missing fields: {missing_fields}"
                else:
                    # Validate glucose categorization
                    expected_category = self.get_expected_category(glucose_value)
                    if data["category"] != expected_category:
                        success = False
                        details += f", Wrong category: got {data['category']}, expected {expected_category}"
                    else:
                        details += f", Category: {data['category']}, Value: {data['glucose_value']}"
                        return data  # Return the created reading for further tests
            
            self.log_test(f"POST Glucose Reading ({glucose_value} mg/dL)", success, details)
            return data if success else None
            
        except Exception as e:
            self.log_test(f"POST Glucose Reading ({glucose_value} mg/dL)", False, str(e))
            return None

    def get_expected_category(self, value: float) -> str:
        """Get expected category for glucose value"""
        if value < 70:
            return "Hipoglicemia"
        elif 70 <= value <= 140:
            return "Normal"
        elif 141 <= value <= 199:
            return "Atenção"
        else:
            return "Alerta"

    def test_get_latest_glucose(self):
        """Test GET /api/glucose/latest endpoint"""
        try:
            response = requests.get(f"{self.base_url}/api/glucose/latest")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                data = response.json()
                if data is None:
                    details += ", No readings found (empty database)"
                else:
                    details += f", Latest reading: {data.get('glucose_value')} mg/dL, Category: {data.get('category')}"
            
            self.log_test("GET Latest Glucose", success, details)
            return data if success else None
            
        except Exception as e:
            self.log_test("GET Latest Glucose", False, str(e))
            return None

    def test_get_glucose_history(self, limit: int = 10):
        """Test GET /api/glucose/history endpoint"""
        try:
            response = requests.get(f"{self.base_url}/api/glucose/history?limit={limit}")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                data = response.json()
                details += f", History count: {len(data)}"
                if data:
                    details += f", First reading: {data[0].get('glucose_value')} mg/dL"
            
            self.log_test("GET Glucose History", success, details)
            return data if success else None
            
        except Exception as e:
            self.log_test("GET Glucose History", False, str(e))
            return None

    def test_get_glucose_stats(self):
        """Test GET /api/glucose/stats endpoint"""
        try:
            response = requests.get(f"{self.base_url}/api/glucose/stats")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                data = response.json()
                required_fields = ["total_readings", "average_glucose", "category_distribution"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    success = False
                    details += f", Missing fields: {missing_fields}"
                else:
                    details += f", Total: {data['total_readings']}, Avg: {data['average_glucose']}"
            
            self.log_test("GET Glucose Stats", success, details)
            return data if success else None
            
        except Exception as e:
            self.log_test("GET Glucose Stats", False, str(e))
            return None

    def test_clear_readings(self):
        """Test DELETE /api/glucose/clear endpoint"""
        try:
            response = requests.delete(f"{self.base_url}/api/glucose/clear")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                data = response.json()
                details += f", {data.get('message', 'No message')}"
            
            self.log_test("DELETE Clear Readings", success, details)
            return success
            
        except Exception as e:
            self.log_test("DELETE Clear Readings", False, str(e))
            return False

    def test_glucose_categorization(self):
        """Test glucose categorization logic with all ranges"""
        print("\n🧪 Testing Glucose Categorization Logic...")
        
        test_cases = [
            (65, "Hipoglicemia"),   # < 70
            (95, "Normal"),         # 70-140
            (180, "Atenção"),       # 141-199
            (220, "Alerta")         # >= 200
        ]
        
        categorization_passed = 0
        for glucose_value, expected_category in test_cases:
            reading = self.test_post_glucose_reading(glucose_value)
            if reading and reading.get("category") == expected_category:
                categorization_passed += 1
        
        success = categorization_passed == len(test_cases)
        self.log_test("Glucose Categorization Logic", success, 
                     f"{categorization_passed}/{len(test_cases)} categories correct")
        return success

    def run_comprehensive_test(self):
        """Run all tests in sequence"""
        print("🚀 Starting NeoView Glucose Monitor API Tests")
        print(f"🌐 Testing against: {self.base_url}")
        print("=" * 60)
        
        # Test 1: Root endpoint
        if not self.test_root_endpoint():
            print("❌ Root endpoint failed - API may be down")
            return False
        
        # Test 2: Clear existing data for clean testing
        print("\n🧹 Clearing existing data...")
        self.test_clear_readings()
        
        # Test 3: Test glucose categorization
        self.test_glucose_categorization()
        
        # Test 4: Test data retrieval endpoints
        print("\n📊 Testing data retrieval...")
        self.test_get_latest_glucose()
        self.test_get_glucose_history()
        self.test_get_glucose_stats()
        
        # Test 5: Add more test data
        print("\n📝 Adding more test data...")
        test_readings = [120, 75, 160, 45, 250, 90, 185]
        for value in test_readings:
            self.test_post_glucose_reading(value)
        
        # Test 6: Verify data persistence
        print("\n🔍 Verifying data persistence...")
        latest = self.test_get_latest_glucose()
        history = self.test_get_glucose_history(limit=20)
        stats = self.test_get_glucose_stats()
        
        # Validate data consistency
        if history and stats:
            expected_count = len(test_readings) + 4  # 4 from categorization test
            actual_count = stats.get("total_readings", 0)
            if actual_count >= expected_count:
                self.log_test("Data Persistence", True, f"Expected >= {expected_count}, got {actual_count}")
            else:
                self.log_test("Data Persistence", False, f"Expected >= {expected_count}, got {actual_count}")
        
        return True

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📋 TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("🎉 ALL TESTS PASSED! API is working correctly.")
        else:
            print("⚠️  Some tests failed. Check the details above.")
            print("\nFailed Tests:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['name']}: {result['details']}")

def main():
    """Main test execution"""
    tester = NeoViewAPITester()
    
    try:
        success = tester.run_comprehensive_test()
        tester.print_summary()
        return 0 if tester.tests_passed == tester.tests_run else 1
        
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())