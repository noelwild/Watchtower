#!/usr/bin/env python3
"""
Detailed EBA Compliance API Testing
Tests the specific requirements from the review request
"""

import requests
import json
from datetime import datetime

class EBAComplianceDetailedTester:
    def __init__(self):
        self.base_url = "https://d10b92a2-8b37-41ef-8865-be6746ac4c76.preview.emergentagent.com"
        self.api_url = f"{self.base_url}/api"
        self.token = None
        
    def login(self):
        """Login with demo credentials VP12345/password123"""
        response = requests.post(
            f"{self.api_url}/auth/login",
            json={"vp_number": "VP12345", "password": "password123"},
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            data = response.json()
            self.token = data['access_token']
            print(f"✅ Successfully logged in as {data['user']['name']} ({data['user']['role']})")
            return True
        else:
            print(f"❌ Login failed: {response.text}")
            return False
    
    def get_headers(self):
        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.token}'
        }
    
    def test_eba_warnings_detail(self):
        """Test GET /api/analytics/eba-warnings-detail"""
        print("\n🔍 Testing EBA Warnings Detail Endpoint")
        response = requests.get(f"{self.api_url}/analytics/eba-warnings-detail", headers=self.get_headers())
        
        if response.status_code != 200:
            print(f"❌ Failed with status {response.status_code}: {response.text}")
            return False
            
        data = response.json()
        print(f"✅ Endpoint accessible - returned {len(data)} members with warnings")
        
        # Verify data structure
        if data:
            member = data[0]
            required_fields = ['member_id', 'member_name', 'station', 'rank', 'warnings', 'fortnight_hours']
            missing = [f for f in required_fields if f not in member]
            if missing:
                print(f"⚠️  Missing required fields: {missing}")
            else:
                print("✅ All required fields present")
                print(f"   Sample: {member['member_name']} has {len(member['warnings'])} warnings")
        
        return True
    
    def test_eba_compliant_members(self):
        """Test GET /api/analytics/eba-compliant-members"""
        print("\n🔍 Testing EBA Compliant Members Endpoint")
        response = requests.get(f"{self.api_url}/analytics/eba-compliant-members", headers=self.get_headers())
        
        if response.status_code != 200:
            print(f"❌ Failed with status {response.status_code}: {response.text}")
            return False
            
        data = response.json()
        print(f"✅ Endpoint accessible - returned {len(data)} compliant members")
        
        # Verify data structure
        if data:
            member = data[0]
            required_fields = ['member_id', 'member_name', 'station', 'rank', 'compliance', 'fortnight_hours']
            missing = [f for f in required_fields if f not in member]
            if missing:
                print(f"⚠️  Missing required fields: {missing}")
            else:
                print("✅ All required fields present")
                print(f"   Sample: {member['member_name']} - {member['fortnight_hours']}h fortnight")
                
                # Verify compliance status is "compliant"
                if member.get('compliance', {}).get('status') == 'compliant':
                    print("✅ Compliance status correctly set to 'compliant'")
                else:
                    print(f"⚠️  Expected compliance status 'compliant', got '{member.get('compliance', {}).get('status')}'")
        
        return True
    
    def test_over_76_hours(self):
        """Test GET /api/analytics/over-76-hours"""
        print("\n🔍 Testing Over 76 Hours Endpoint")
        response = requests.get(f"{self.api_url}/analytics/over-76-hours", headers=self.get_headers())
        
        if response.status_code != 200:
            print(f"❌ Failed with status {response.status_code}: {response.text}")
            return False
            
        data = response.json()
        print(f"✅ Endpoint accessible - returned {len(data)} members over 76 hours")
        
        # Verify data structure and business logic
        if data:
            member = data[0]
            required_fields = ['member_id', 'member_name', 'station', 'rank', 'fortnight_hours', 'overage_hours', 'severity']
            missing = [f for f in required_fields if f not in member]
            if missing:
                print(f"⚠️  Missing required fields: {missing}")
            else:
                print("✅ All required fields present")
                
                # Verify all members are actually over 76 hours
                all_over_76 = all(m['fortnight_hours'] > 76 for m in data)
                if all_over_76:
                    print("✅ All members correctly exceed 76-hour limit")
                else:
                    print("⚠️  Some members don't exceed 76-hour limit")
                
                # Verify urgency-based sorting (highest overage first)
                is_sorted = all(data[i]['overage_hours'] >= data[i+1]['overage_hours'] for i in range(len(data)-1))
                if is_sorted:
                    print("✅ Results properly sorted by urgency (highest overage first)")
                else:
                    print("⚠️  Results not properly sorted by overage hours")
                
                # Show most critical member
                most_critical = data[0]
                print(f"   Most critical: {most_critical['member_name']} - {most_critical['fortnight_hours']:.1f}h ({most_critical['overage_hours']:.1f}h over, {most_critical['severity']} severity)")
        
        return True
    
    def test_approaching_76_hours(self):
        """Test GET /api/analytics/approaching-76-hours"""
        print("\n🔍 Testing Approaching 76 Hours Endpoint")
        response = requests.get(f"{self.api_url}/analytics/approaching-76-hours", headers=self.get_headers())
        
        if response.status_code != 200:
            print(f"❌ Failed with status {response.status_code}: {response.text}")
            return False
            
        data = response.json()
        print(f"✅ Endpoint accessible - returned {len(data)} members approaching 76 hours")
        
        # Verify data structure and business logic
        if data:
            member = data[0]
            required_fields = ['member_id', 'member_name', 'station', 'rank', 'fortnight_hours', 'remaining_hours', 'utilization_percent', 'risk_level']
            missing = [f for f in required_fields if f not in member]
            if missing:
                print(f"⚠️  Missing required fields: {missing}")
            else:
                print("✅ All required fields present")
                
                # Verify all members are in 65-76 hour range
                in_range = all(65 <= m['fortnight_hours'] <= 76 for m in data)
                if in_range:
                    print("✅ All members correctly in 65-76 hour range")
                else:
                    print("⚠️  Some members outside expected 65-76 hour range")
                
                # Verify sorting (highest hours first)
                is_sorted = all(data[i]['fortnight_hours'] >= data[i+1]['fortnight_hours'] for i in range(len(data)-1))
                if is_sorted:
                    print("✅ Results properly sorted by fortnight hours (highest first)")
                else:
                    print("⚠️  Results not properly sorted by fortnight hours")
                
                # Show highest risk member
                highest_risk = data[0]
                print(f"   Highest risk: {highest_risk['member_name']} - {highest_risk['fortnight_hours']:.1f}h ({highest_risk['utilization_percent']:.1f}% utilization, {highest_risk['risk_level']} risk)")
        
        return True
    
    def test_authentication_requirements(self):
        """Test that all endpoints require authentication"""
        print("\n🔒 Testing Authentication Requirements")
        
        endpoints = [
            "analytics/eba-warnings-detail",
            "analytics/eba-compliant-members", 
            "analytics/over-76-hours",
            "analytics/approaching-76-hours"
        ]
        
        all_protected = True
        for endpoint in endpoints:
            response = requests.get(f"{self.api_url}/{endpoint}")
            if response.status_code == 403:
                print(f"✅ {endpoint} properly protected (403)")
            else:
                print(f"⚠️  {endpoint} returned {response.status_code} instead of 403")
                all_protected = False
        
        return all_protected
    
    def run_all_tests(self):
        """Run all EBA compliance tests"""
        print("🚀 Starting Detailed EBA Compliance API Tests")
        print("=" * 60)
        
        # Initialize sample data first
        print("\n📊 Initializing sample data...")
        init_response = requests.post(f"{self.api_url}/init-sample-data")
        if init_response.status_code == 200:
            print("✅ Sample data initialized")
        else:
            print(f"⚠️  Sample data initialization returned {init_response.status_code}")
        
        # Login
        if not self.login():
            return False
        
        # Run all tests
        tests = [
            self.test_eba_warnings_detail,
            self.test_eba_compliant_members,
            self.test_over_76_hours,
            self.test_approaching_76_hours,
            self.test_authentication_requirements
        ]
        
        passed = 0
        for test in tests:
            try:
                if test():
                    passed += 1
            except Exception as e:
                print(f"❌ Test failed with exception: {e}")
        
        print("\n" + "=" * 60)
        print(f"📊 DETAILED TEST RESULTS: {passed}/{len(tests)} tests passed")
        
        if passed == len(tests):
            print("🎉 All EBA compliance endpoints working correctly!")
            return True
        else:
            print(f"⚠️  {len(tests) - passed} tests had issues")
            return False

if __name__ == "__main__":
    tester = EBAComplianceDetailedTester()
    success = tester.run_all_tests()
    exit(0 if success else 1)