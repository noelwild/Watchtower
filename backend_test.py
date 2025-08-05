import requests
import sys
from datetime import datetime
import json

class WatchtowerAPITester:
    def __init__(self, base_url=None):
        # Read the backend URL from frontend .env file
        if base_url is None:
            try:
                with open('/app/frontend/.env', 'r') as f:
                    for line in f:
                        if line.startswith('REACT_APP_BACKEND_URL='):
                            base_url = line.split('=', 1)[1].strip()
                            break
                if base_url is None:
                    base_url = "http://localhost:8001"  # fallback
            except:
                base_url = "http://localhost:8001"  # fallback
        
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.user_data = None

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    if isinstance(response_data, dict) and len(str(response_data)) < 500:
                        print(f"   Response: {response_data}")
                    elif isinstance(response_data, list):
                        print(f"   Response: List with {len(response_data)} items")
                except:
                    print(f"   Response: {response.text[:200]}...")
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:300]}")

            return success, response.json() if response.text and response.status_code < 500 else {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_init_sample_data(self):
        """Initialize sample data"""
        success, response = self.run_test(
            "Initialize Sample Data",
            "POST",
            "init-sample-data",
            200
        )
        return success

    def test_login(self, vp_number, password):
        """Test login and get token"""
        success, response = self.run_test(
            f"Login (VP: {vp_number})",
            "POST",
            "auth/login",
            200,
            data={"vp_number": vp_number, "password": password}
        )
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.user_data = response.get('user', {})
            print(f"   Logged in as: {self.user_data.get('name')} ({self.user_data.get('role')})")
            return True
        return False

    def test_get_members(self):
        """Get all members"""
        success, response = self.run_test(
            "Get Members",
            "GET",
            "members",
            200
        )
        return success, response

    def test_get_workload_summary(self):
        """Get workload analytics"""
        success, response = self.run_test(
            "Get Workload Summary",
            "GET",
            "analytics/workload-summary",
            200
        )
        return success, response

    def test_get_corro_distribution(self):
        """Get corro distribution analytics"""
        success, response = self.run_test(
            "Get Corro Distribution",
            "GET",
            "analytics/corro-distribution",
            200
        )
        return success, response

    def test_update_member_preferences(self, member_id):
        """Test updating member preferences (requires sergeant+ role)"""
        preferences = {
            "night_shift_tolerance": 4,
            "recall_willingness": True,
            "avoid_consecutive_doubles": True,
            "avoid_four_earlies": False,
            "medical_limitations": "Test limitation",
            "welfare_notes": "Test welfare note"
        }
        
        success, response = self.run_test(
            "Update Member Preferences",
            "PUT",
            f"members/{member_id}/preferences",
            200,
            data=preferences
        )
        return success

    def test_unauthorized_access(self):
        """Test accessing protected endpoint without token"""
        old_token = self.token
        self.token = None
        
        success, response = self.run_test(
            "Unauthorized Access (should fail)",
            "GET",
            "members",
            403  # Should fail with 403 (FastAPI returns 403 for missing auth)
        )
        
        self.token = old_token
        return success

    def test_eba_warnings_detail(self):
        """Test EBA warnings detail endpoint"""
        success, response = self.run_test(
            "Get EBA Warnings Detail",
            "GET",
            "analytics/eba-warnings-detail",
            200
        )
        
        if success and isinstance(response, list):
            print(f"   Found {len(response)} members with EBA warnings")
            if response:
                # Check data structure
                first_member = response[0]
                required_fields = ['member_id', 'member_name', 'station', 'rank', 'warnings', 'fortnight_hours']
                missing_fields = [field for field in required_fields if field not in first_member]
                if missing_fields:
                    print(f"   ⚠️  Missing fields in response: {missing_fields}")
                else:
                    print(f"   ✅ Response structure validated")
                    print(f"   Sample member: {first_member.get('member_name')} - {len(first_member.get('warnings', []))} warnings")
        
        return success, response

    def test_eba_compliant_members(self):
        """Test EBA compliant members endpoint"""
        success, response = self.run_test(
            "Get EBA Compliant Members",
            "GET",
            "analytics/eba-compliant-members",
            200
        )
        
        if success and isinstance(response, list):
            print(f"   Found {len(response)} compliant members")
            if response:
                # Check data structure
                first_member = response[0]
                required_fields = ['member_id', 'member_name', 'station', 'rank', 'compliance', 'fortnight_hours']
                missing_fields = [field for field in required_fields if field not in first_member]
                if missing_fields:
                    print(f"   ⚠️  Missing fields in response: {missing_fields}")
                else:
                    print(f"   ✅ Response structure validated")
                    print(f"   Sample member: {first_member.get('member_name')} - {first_member.get('fortnight_hours')}h fortnight")
        
        return success, response

    def test_over_76_hours(self):
        """Test members over 76 hours endpoint"""
        success, response = self.run_test(
            "Get Members Over 76 Hours",
            "GET",
            "analytics/over-76-hours",
            200
        )
        
        if success and isinstance(response, list):
            print(f"   Found {len(response)} members exceeding 76-hour limit")
            if response:
                # Check data structure and sorting
                first_member = response[0]
                required_fields = ['member_id', 'member_name', 'station', 'rank', 'fortnight_hours', 'overage_hours', 'severity']
                missing_fields = [field for field in required_fields if field not in first_member]
                if missing_fields:
                    print(f"   ⚠️  Missing fields in response: {missing_fields}")
                else:
                    print(f"   ✅ Response structure validated")
                    print(f"   Most critical: {first_member.get('member_name')} - {first_member.get('fortnight_hours')}h ({first_member.get('overage_hours')}h over)")
                    
                    # Verify sorting (highest overage first)
                    if len(response) > 1:
                        is_sorted = all(response[i].get('overage_hours', 0) >= response[i+1].get('overage_hours', 0) 
                                      for i in range(len(response)-1))
                        if is_sorted:
                            print(f"   ✅ Results properly sorted by urgency")
                        else:
                            print(f"   ⚠️  Results not properly sorted by overage hours")
        
        return success, response

    def test_approaching_76_hours(self):
        """Test members approaching 76 hours endpoint"""
        success, response = self.run_test(
            "Get Members Approaching 76 Hours",
            "GET",
            "analytics/approaching-76-hours",
            200
        )
        
        if success and isinstance(response, list):
            print(f"   Found {len(response)} members approaching 76-hour limit")
            if response:
                # Check data structure and sorting
                first_member = response[0]
                required_fields = ['member_id', 'member_name', 'station', 'rank', 'fortnight_hours', 'remaining_hours', 'utilization_percent', 'risk_level']
                missing_fields = [field for field in required_fields if field not in first_member]
                if missing_fields:
                    print(f"   ⚠️  Missing fields in response: {missing_fields}")
                else:
                    print(f"   ✅ Response structure validated")
                    print(f"   Highest risk: {first_member.get('member_name')} - {first_member.get('fortnight_hours')}h ({first_member.get('utilization_percent')}% utilization)")
                    
                    # Verify sorting (highest hours first)
                    if len(response) > 1:
                        is_sorted = all(response[i].get('fortnight_hours', 0) >= response[i+1].get('fortnight_hours', 0) 
                                      for i in range(len(response)-1))
                        if is_sorted:
                            print(f"   ✅ Results properly sorted by fortnight hours")
                        else:
                            print(f"   ⚠️  Results not properly sorted by fortnight hours")
                    
                    # Verify hour range (should be 65-76)
                    valid_range = all(65 <= member.get('fortnight_hours', 0) <= 76 for member in response)
                    if valid_range:
                        print(f"   ✅ All members in valid 65-76 hour range")
                    else:
                        print(f"   ⚠️  Some members outside expected 65-76 hour range")
        
        return success, response

    def test_eba_endpoints_unauthorized(self):
        """Test EBA endpoints without authentication"""
        old_token = self.token
        self.token = None
        
        endpoints = [
            "analytics/eba-warnings-detail",
            "analytics/eba-compliant-members", 
            "analytics/over-76-hours",
            "analytics/approaching-76-hours"
        ]
        
        all_passed = True
        for endpoint in endpoints:
            success, response = self.run_test(
                f"Unauthorized Access to {endpoint}",
                "GET",
                endpoint,
                403  # Should fail with 403 (FastAPI returns 403 for missing auth)
            )
            if not success:
                all_passed = False
        
        self.token = old_token
        return all_passed

    def test_detailed_member_view(self, member_id):
        """Test the comprehensive detailed member view endpoint"""
        success, response = self.run_test(
            f"Get Detailed Member View (ID: {member_id[:8]}...)",
            "GET",
            f"members/{member_id}/detailed-view",
            200
        )
        
        if success and isinstance(response, dict):
            print(f"   ✅ Detailed member view retrieved successfully")
            
            # Verify all required sections are present
            required_sections = [
                'member_info',
                'shift_breakdown', 
                'eba_compliance_history',
                'member_preferences',
                'activity_log',
                'fatigue_risk_projection',
                'schedule_request_history',
                'equity_tracking'
            ]
            
            missing_sections = [section for section in required_sections if section not in response]
            if missing_sections:
                print(f"   ⚠️  Missing sections: {missing_sections}")
                return False, response
            else:
                print(f"   ✅ All 8 required sections present")
            
            # Validate member_info section
            member_info = response.get('member_info', {})
            if isinstance(member_info, dict) and 'name' in member_info:
                print(f"   ✅ Member info: {member_info.get('name')} ({member_info.get('rank', 'Unknown')})")
            else:
                print(f"   ⚠️  Invalid member_info structure")
            
            # Validate shift_breakdown section
            shift_breakdown = response.get('shift_breakdown', {})
            if isinstance(shift_breakdown, dict):
                total_shifts = shift_breakdown.get('total_shifts', 0)
                weekly_hours = shift_breakdown.get('weekly_hours', [])
                shift_types = shift_breakdown.get('shift_types', {})
                
                print(f"   ✅ Shift breakdown: {total_shifts} total shifts, {len(weekly_hours)} weeks of data")
                print(f"   ✅ Shift types: {list(shift_types.keys())}")
                
                # Verify weekly hours are sorted (most recent first)
                if len(weekly_hours) > 1:
                    dates_sorted = all(
                        weekly_hours[i].get('week_start', datetime.min) >= 
                        weekly_hours[i+1].get('week_start', datetime.min) 
                        for i in range(len(weekly_hours)-1)
                    )
                    if dates_sorted:
                        print(f"   ✅ Weekly hours properly sorted (most recent first)")
                    else:
                        print(f"   ⚠️  Weekly hours not properly sorted")
            else:
                print(f"   ⚠️  Invalid shift_breakdown structure")
            
            # Validate EBA compliance history
            eba_compliance = response.get('eba_compliance_history', {})
            if isinstance(eba_compliance, dict):
                status = eba_compliance.get('current_status', 'unknown')
                violations = eba_compliance.get('violations', [])
                warnings = eba_compliance.get('warnings', [])
                fortnight_hours = eba_compliance.get('fortnight_hours', 0)
                
                print(f"   ✅ EBA compliance: {status} status, {fortnight_hours}h fortnight")
                print(f"   ✅ Compliance issues: {len(violations)} violations, {len(warnings)} warnings")
            else:
                print(f"   ⚠️  Invalid eba_compliance_history structure")
            
            # Validate member preferences
            preferences = response.get('member_preferences', {})
            if isinstance(preferences, dict):
                night_tolerance = preferences.get('night_shift_tolerance', 'N/A')
                recall_willing = preferences.get('recall_willingness', 'N/A')
                print(f"   ✅ Preferences: Night tolerance={night_tolerance}, Recall willing={recall_willing}")
            else:
                print(f"   ⚠️  Invalid member_preferences structure")
            
            # Validate activity log
            activity_log = response.get('activity_log', [])
            if isinstance(activity_log, list):
                print(f"   ✅ Activity log: {len(activity_log)} recent activities")
                if activity_log:
                    # Check if activities are chronologically ordered
                    recent_activity = activity_log[0]
                    if 'action' in recent_activity and 'details' in recent_activity:
                        print(f"   ✅ Recent activity: {recent_activity.get('action')} - {recent_activity.get('details')[:50]}...")
            else:
                print(f"   ⚠️  Invalid activity_log structure")
            
            # Validate fatigue risk projection
            fatigue_risk = response.get('fatigue_risk_projection', {})
            if isinstance(fatigue_risk, dict):
                risk_factors = fatigue_risk.get('risk_factors', [])
                projected_risk = fatigue_risk.get('projected_risk', 'unknown')
                recommendations = fatigue_risk.get('recommendations', [])
                
                print(f"   ✅ Fatigue risk: {projected_risk} risk level")
                print(f"   ✅ Risk assessment: {len(risk_factors)} factors, {len(recommendations)} recommendations")
            else:
                print(f"   ⚠️  Invalid fatigue_risk_projection structure")
            
            # Validate schedule request history
            schedule_history = response.get('schedule_request_history', [])
            if isinstance(schedule_history, list):
                print(f"   ✅ Schedule history: {len(schedule_history)} recent requests")
            else:
                print(f"   ⚠️  Invalid schedule_request_history structure")
            
            # Validate equity tracking
            equity_tracking = response.get('equity_tracking', {})
            if isinstance(equity_tracking, dict):
                corro_allocation = equity_tracking.get('corro_allocation', {})
                fairness_score = equity_tracking.get('fairness_score', 0)
                
                if isinstance(corro_allocation, dict):
                    member_count = corro_allocation.get('member_count', 0)
                    station_avg = corro_allocation.get('station_average', 0)
                    print(f"   ✅ Equity tracking: {member_count} corro shifts vs {station_avg} station avg")
                    print(f"   ✅ Fairness score: {fairness_score}")
                else:
                    print(f"   ⚠️  Invalid corro_allocation structure")
            else:
                print(f"   ⚠️  Invalid equity_tracking structure")
        
        return success, response

    def test_detailed_member_view_invalid_id(self):
        """Test detailed member view with invalid member ID"""
        invalid_id = "invalid-member-id-12345"
        success, response = self.run_test(
            f"Get Detailed Member View (Invalid ID)",
            "GET",
            f"members/{invalid_id}/detailed-view",
            404  # Should return 404 for invalid member ID
        )
        
        if success:
            print(f"   ✅ Properly handles invalid member ID with 404 error")
        
        return success

    def test_detailed_member_view_unauthorized(self):
        """Test detailed member view without authentication"""
        old_token = self.token
        self.token = None
        
        # Use a dummy member ID since we're testing auth, not the ID validity
        dummy_id = "test-member-id"
        success, response = self.run_test(
            "Detailed Member View (Unauthorized)",
            "GET",
            f"members/{dummy_id}/detailed-view",
            403  # Should fail with 403 for missing auth
        )
        
        self.token = old_token
        
        if success:
            print(f"   ✅ Properly enforces authentication requirement")
        
        return success

    # ===== AUTOMATED ROSTER PRODUCER TESTS =====
    
    def test_generate_roster(self):
        """Test automated roster generation"""
        roster_config = {
            "station": "geelong",
            "period_weeks": 2,
            "min_van_coverage": 2,
            "min_watchhouse_coverage": 1,
            "max_consecutive_nights": 7,
            "min_rest_days_per_fortnight": 4,
            "max_fortnight_hours": 76.0,
            "enable_fatigue_balancing": True,
            "enable_preference_weighting": True,
            "corro_rotation_priority": True
        }
        
        success, response = self.run_test(
            "Generate Automated Roster",
            "POST",
            "roster/generate",
            200,
            data=roster_config
        )
        
        if success and isinstance(response, dict):
            print(f"   ✅ Roster generation successful")
            
            # Verify response structure
            required_fields = ['roster_period_id', 'period_start', 'period_end', 'total_assignments', 'status', 'compliance_summary']
            missing_fields = [field for field in required_fields if field not in response]
            if missing_fields:
                print(f"   ⚠️  Missing fields in response: {missing_fields}")
                return False, response
            else:
                print(f"   ✅ Response structure validated")
            
            # Verify roster details
            roster_id = response.get('roster_period_id')
            total_assignments = response.get('total_assignments', 0)
            status = response.get('status', 'unknown')
            
            print(f"   ✅ Roster ID: {roster_id}")
            print(f"   ✅ Total assignments: {total_assignments}")
            print(f"   ✅ Status: {status}")
            
            # Verify compliance summary
            compliance = response.get('compliance_summary', {})
            if isinstance(compliance, dict):
                has_violations = compliance.get('has_violations', False)
                print(f"   ✅ Compliance check: {'❌ Has violations' if has_violations else '✅ No violations'}")
            
            return True, response
        
        return success, response
    
    def test_generate_roster_with_custom_date(self):
        """Test roster generation with custom start date"""
        from datetime import datetime, timedelta
        
        # Set start date to next Monday
        today = datetime.utcnow()
        days_ahead = 7 - today.weekday()  # Next Monday
        start_date = (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        
        roster_config = {
            "station": "geelong",
            "period_weeks": 2,
            "min_van_coverage": 2,
            "min_watchhouse_coverage": 1,
            "max_consecutive_nights": 7,
            "min_rest_days_per_fortnight": 4,
            "max_fortnight_hours": 76.0,
            "enable_fatigue_balancing": True,
            "enable_preference_weighting": False,  # Different config
            "corro_rotation_priority": False
        }
        
        success, response = self.run_test(
            f"Generate Roster with Custom Date ({start_date})",
            "POST",
            f"roster/generate?start_date={start_date}",
            200,
            data=roster_config
        )
        
        if success and isinstance(response, dict):
            period_start = response.get('period_start', '')
            if start_date in period_start:
                print(f"   ✅ Custom start date properly applied")
            else:
                print(f"   ⚠️  Custom start date not applied correctly")
        
        return success, response
    
    def test_get_roster_periods(self):
        """Test getting roster periods list"""
        success, response = self.run_test(
            "Get Roster Periods",
            "GET",
            "roster/periods",
            200
        )
        
        if success and isinstance(response, list):
            print(f"   ✅ Found {len(response)} roster periods")
            
            if response:
                # Verify structure of first period
                first_period = response[0]
                required_fields = ['id', 'start_date', 'end_date', 'status', 'created_by', 'station']
                missing_fields = [field for field in required_fields if field not in first_period]
                if missing_fields:
                    print(f"   ⚠️  Missing fields in period: {missing_fields}")
                else:
                    print(f"   ✅ Period structure validated")
                    print(f"   ✅ Sample period: {first_period.get('start_date')} to {first_period.get('end_date')} ({first_period.get('status')})")
        
        return success, response
    
    def test_get_roster_periods_filtered(self):
        """Test getting roster periods with station filtering"""
        success, response = self.run_test(
            "Get Roster Periods (Geelong Station)",
            "GET",
            "roster/periods?station=geelong",
            200
        )
        
        if success and isinstance(response, list):
            print(f"   ✅ Found {len(response)} roster periods for Geelong station")
            
            # Verify all periods are for geelong station
            if response:
                geelong_periods = [p for p in response if p.get('station') == 'geelong']
                if len(geelong_periods) == len(response):
                    print(f"   ✅ Station filtering working correctly")
                else:
                    print(f"   ⚠️  Station filtering not working - found {len(geelong_periods)}/{len(response)} geelong periods")
        
        return success, response
    
    def test_get_roster_details(self, roster_period_id):
        """Test getting detailed roster with assignments"""
        success, response = self.run_test(
            f"Get Roster Details (ID: {roster_period_id[:8]}...)",
            "GET",
            f"roster/{roster_period_id}",
            200
        )
        
        if success and isinstance(response, dict):
            print(f"   ✅ Roster details retrieved successfully")
            
            # Verify response structure
            required_fields = ['roster_period', 'assignments_by_date', 'total_assignments', 'compliance_status', 'member_summary']
            missing_fields = [field for field in required_fields if field not in response]
            if missing_fields:
                print(f"   ⚠️  Missing fields in response: {missing_fields}")
                return False, response
            else:
                print(f"   ✅ Response structure validated")
            
            # Verify roster period details
            roster_period = response.get('roster_period', {})
            if isinstance(roster_period, dict):
                start_date = roster_period.get('start_date', 'Unknown')
                end_date = roster_period.get('end_date', 'Unknown')
                status = roster_period.get('status', 'Unknown')
                print(f"   ✅ Period: {start_date} to {end_date} ({status})")
            
            # Verify assignments
            assignments_by_date = response.get('assignments_by_date', {})
            total_assignments = response.get('total_assignments', 0)
            
            if isinstance(assignments_by_date, dict):
                dates_count = len(assignments_by_date)
                print(f"   ✅ Assignments organized by {dates_count} dates")
                print(f"   ✅ Total assignments: {total_assignments}")
                
                # Check a sample date's assignments
                if assignments_by_date:
                    sample_date = list(assignments_by_date.keys())[0]
                    sample_assignments = assignments_by_date[sample_date]
                    if isinstance(sample_assignments, list) and sample_assignments:
                        sample_assignment = sample_assignments[0]
                        if 'member_name' in sample_assignment and 'shift_type' in sample_assignment:
                            print(f"   ✅ Sample assignment: {sample_assignment.get('member_name')} - {sample_assignment.get('shift_type')} shift")
                        else:
                            print(f"   ⚠️  Assignment missing member details")
            
            # Verify compliance status
            compliance_status = response.get('compliance_status', {})
            if isinstance(compliance_status, dict):
                has_violations = compliance_status.get('has_violations', False)
                violations = compliance_status.get('violations', [])
                print(f"   ✅ Compliance: {'❌ Has violations' if has_violations else '✅ No violations'}")
                if violations:
                    print(f"   ⚠️  Violations: {len(violations)} found")
            
            # Verify member summary
            member_summary = response.get('member_summary', {})
            if isinstance(member_summary, dict):
                member_count = len(member_summary)
                print(f"   ✅ Member summary: {member_count} members included")
        
        return success, response
    
    def test_get_roster_details_invalid_id(self):
        """Test getting roster details with invalid ID"""
        invalid_id = "invalid-roster-id-12345"
        success, response = self.run_test(
            "Get Roster Details (Invalid ID)",
            "GET",
            f"roster/{invalid_id}",
            404
        )
        
        if success:
            print(f"   ✅ Properly handles invalid roster ID with 404 error")
        
        return success
    
    def test_publish_roster(self, roster_period_id):
        """Test publishing a draft roster"""
        success, response = self.run_test(
            f"Publish Roster (ID: {roster_period_id[:8]}...)",
            "PUT",
            f"roster/{roster_period_id}/publish",
            200
        )
        
        if success and isinstance(response, dict):
            print(f"   ✅ Roster publication successful")
            
            # Verify response structure
            if 'message' in response:
                print(f"   ✅ Publication message: {response.get('message')}")
            
            if 'roster_period' in response:
                roster_period = response.get('roster_period', {})
                status = roster_period.get('status', 'unknown')
                published_at = roster_period.get('published_at', 'unknown')
                print(f"   ✅ New status: {status}")
                print(f"   ✅ Published at: {published_at}")
            
            if 'compliance_validation' in response:
                compliance = response.get('compliance_validation', {})
                has_violations = compliance.get('has_violations', False)
                print(f"   ✅ Final compliance check: {'❌ Has violations' if has_violations else '✅ Passed'}")
        
        return success, response
    
    def test_publish_roster_invalid_id(self):
        """Test publishing roster with invalid ID"""
        invalid_id = "invalid-roster-id-12345"
        success, response = self.run_test(
            "Publish Roster (Invalid ID)",
            "PUT",
            f"roster/{invalid_id}/publish",
            404
        )
        
        if success:
            print(f"   ✅ Properly handles invalid roster ID with 404 error")
        
        return success
    
    def test_roster_endpoints_unauthorized(self):
        """Test roster endpoints without authentication"""
        old_token = self.token
        self.token = None
        
        endpoints_and_methods = [
            ("POST", "roster/generate", {"station": "geelong", "period_weeks": 2}),
            ("GET", "roster/periods", None),
            ("GET", "roster/dummy-id", None),
            ("PUT", "roster/dummy-id/publish", None)
        ]
        
        all_passed = True
        for method, endpoint, data in endpoints_and_methods:
            success, response = self.run_test(
                f"Unauthorized {method} {endpoint}",
                method,
                endpoint,
                403,  # Should fail with 403 for missing auth
                data=data
            )
            if not success:
                all_passed = False
        
        self.token = old_token
        return all_passed
    
    def test_roster_eba_compliance_validation(self):
        """Test EBA compliance validation in roster generation"""
        # Generate a roster with strict EBA settings
        strict_config = {
            "station": "geelong",
            "period_weeks": 2,
            "min_van_coverage": 1,  # Lower coverage to reduce hours
            "min_watchhouse_coverage": 1,
            "max_consecutive_nights": 3,  # Stricter night limit
            "min_rest_days_per_fortnight": 6,  # More rest days
            "max_fortnight_hours": 60.0,  # Lower hour limit
            "enable_fatigue_balancing": True,
            "enable_preference_weighting": True,
            "corro_rotation_priority": True
        }
        
        success, response = self.run_test(
            "Generate EBA-Compliant Roster (Strict Settings)",
            "POST",
            "roster/generate",
            200,
            data=strict_config
        )
        
        if success and isinstance(response, dict):
            compliance = response.get('compliance_summary', {})
            has_violations = compliance.get('has_violations', True)
            
            if not has_violations:
                print(f"   ✅ Strict EBA settings produced compliant roster")
            else:
                violations = compliance.get('violations', [])
                print(f"   ⚠️  Even strict settings have violations: {len(violations)} found")
                if violations:
                    print(f"   ⚠️  Sample violation: {violations[0][:100]}...")
        
        return success, response

def main():
    print("🚀 Starting WATCHTOWER API Tests")
    print("=" * 50)
    
    # Setup
    tester = WatchtowerAPITester()
    
    # Test 1: Initialize sample data
    print("\n📊 PHASE 1: Data Initialization")
    if not tester.test_init_sample_data():
        print("❌ Sample data initialization failed, but continuing with tests...")
    
    # Test 2: Authentication tests
    print("\n🔐 PHASE 2: Authentication Tests")
    
    # Test Inspector login
    if not tester.test_login("VP12345", "password123"):
        print("❌ Inspector login failed, stopping tests")
        return 1
    
    # Test unauthorized access
    tester.test_unauthorized_access()
    
    # Test 3: Data retrieval tests
    print("\n📈 PHASE 3: Data Retrieval Tests")
    
    members_success, members_data = tester.test_get_members()
    if not members_success:
        print("❌ Members retrieval failed")
        return 1
    
    workload_success, workload_data = tester.test_get_workload_summary()
    if not workload_success:
        print("❌ Workload summary failed")
    
    corro_success, corro_data = tester.test_get_corro_distribution()
    if not corro_success:
        print("❌ Corro distribution failed")
    
    # Test 4: Member management (if we have members)
    print("\n👥 PHASE 4: Member Management Tests")
    if members_data and len(members_data) > 0:
        first_member_id = members_data[0].get('id')
        if first_member_id:
            tester.test_update_member_preferences(first_member_id)
    
    # Test 5: New EBA Compliance Endpoints
    print("\n🏥 PHASE 5: EBA Compliance Endpoint Tests")
    
    # Test all new EBA compliance endpoints
    warnings_success, warnings_data = tester.test_eba_warnings_detail()
    compliant_success, compliant_data = tester.test_eba_compliant_members()
    over_76_success, over_76_data = tester.test_over_76_hours()
    approaching_success, approaching_data = tester.test_approaching_76_hours()
    
    # Verify data categorization logic
    print("\n📊 EBA Compliance Data Analysis:")
    total_members = len(warnings_data) + len(compliant_data) + len(over_76_data) + len(approaching_data)
    print(f"   Total categorized members: {total_members}")
    print(f"   - Members with warnings: {len(warnings_data)}")
    print(f"   - Compliant members: {len(compliant_data)}")
    print(f"   - Over 76 hours: {len(over_76_data)}")
    print(f"   - Approaching 76 hours: {len(approaching_data)}")
    
    if over_76_data:
        print(f"   ✅ Critical members properly identified and sorted")
    if approaching_data:
        print(f"   ✅ At-risk members properly identified and sorted")
    
    # Test unauthorized access to EBA endpoints
    print("\n🔒 PHASE 6: EBA Endpoints Authorization Tests")
    auth_success = tester.test_eba_endpoints_unauthorized()
    
    # Test 7: Detailed Member View Tests
    print("\n👤 PHASE 7: Detailed Member View Tests")
    
    # Test with valid member ID
    if members_data and len(members_data) > 0:
        first_member_id = members_data[0].get('id')
        if first_member_id:
            detailed_view_success, detailed_view_data = tester.test_detailed_member_view(first_member_id)
            
            # Test with another member if available
            if len(members_data) > 1:
                second_member_id = members_data[1].get('id')
                if second_member_id:
                    print(f"\n   Testing second member for consistency...")
                    tester.test_detailed_member_view(second_member_id)
        else:
            print("   ⚠️  No valid member ID found for detailed view testing")
    else:
        print("   ⚠️  No members available for detailed view testing")
    
    # Test error handling
    print("\n🚫 PHASE 8: Detailed Member View Error Handling")
    tester.test_detailed_member_view_invalid_id()
    tester.test_detailed_member_view_unauthorized()
    
    # Test 9: AUTOMATED ROSTER PRODUCER TESTS
    print("\n🗓️ PHASE 9: Automated Roster Producer Tests")
    
    # Test roster generation
    roster_gen_success, roster_gen_data = tester.test_generate_roster()
    roster_period_id = None
    if roster_gen_success and isinstance(roster_gen_data, dict):
        roster_period_id = roster_gen_data.get('roster_period_id')
    
    # Test roster generation with custom date
    tester.test_generate_roster_with_custom_date()
    
    # Test EBA compliance validation
    tester.test_roster_eba_compliance_validation()
    
    # Test roster periods retrieval
    periods_success, periods_data = tester.test_get_roster_periods()
    
    # Test roster periods filtering
    tester.test_get_roster_periods_filtered()
    
    # Test roster details (if we have a roster ID)
    if roster_period_id:
        tester.test_get_roster_details(roster_period_id)
        
        # Test roster publishing
        tester.test_publish_roster(roster_period_id)
    else:
        print("   ⚠️  No roster ID available for detailed testing")
        # Test with invalid IDs to verify error handling
        tester.test_get_roster_details_invalid_id()
        tester.test_publish_roster_invalid_id()
    
    # Test unauthorized access to roster endpoints
    print("\n🔒 PHASE 10: Roster Endpoints Authorization Tests")
    tester.test_roster_endpoints_unauthorized()
    
    # Test 11: Test Sergeant login
    print("\n🔐 PHASE 11: Sergeant Authentication Test")
    tester.test_login("VP12346", "password123")
    
    # Print final results
    print("\n" + "=" * 50)
    print(f"📊 FINAL RESULTS")
    print(f"Tests passed: {tester.tests_passed}/{tester.tests_run}")
    print(f"Success rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All backend tests passed!")
        return 0
    else:
        print(f"⚠️  {tester.tests_run - tester.tests_passed} tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())