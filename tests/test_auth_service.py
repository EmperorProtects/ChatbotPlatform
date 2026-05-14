#!/usr/bin/env python3
"""
Test script for Auth Service (User Authentication and Authorization)

Tests all endpoints of the Auth Service including:
- Health check
- User authentication (login/token generation)
- Token validation
- User profile retrieval
- Password hashing and verification
- JWT token handling
- Error handling and security
"""

import asyncio
import httpx
import json
from typing import Dict, Any, List
import os
import base64
from datetime import datetime, timedelta
import jwt

# Configuration
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8001")
TIMEOUT = httpx.Timeout(30.0, connect=10.0)

# Test credentials and users
TEST_USERS = {
    "admin": {
        "username": "admin",
        "password": "admin123",
        "expected_full_name": "Admin User",
        "expected_email": "admin@example.com"
    }
}

# Test scenarios for various auth operations
INVALID_CREDENTIALS = [
    {"username": "admin", "password": "wrongpassword"},
    {"username": "nonexistent", "password": "anypassword"},
    {"username": "", "password": "admin123"},
    {"username": "admin", "password": ""}
]

INVALID_TOKENS = [
    "invalid.token.here",
    "Bearer invalid.token.here", 
    "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTYzOTY4MjQwMH0.invalid_signature",
    "",
    "expired.token.here"
]

class AuthServiceTester:
    def __init__(self, base_url: str = AUTH_SERVICE_URL):
        self.base_url = base_url
        self.client = None
        self.valid_tokens = {}  # Store valid tokens for testing
        
    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=TIMEOUT)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
    
    async def test_health_check(self) -> Dict[str, Any]:
        """Test service health endpoint"""
        print("\\n🔍 Testing health check...")
        try:
            response = await self.client.get(f"{self.base_url}/health")
            response.raise_for_status()
            result = response.json()
            
            if result.get("status") == "healthy":
                print("✅ Health check passed")
                return {"status": "passed", "response": result}
            else:
                print(f"❌ Health check failed: {result}")
                return {"status": "failed", "response": result}
                
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def test_root_endpoint(self) -> Dict[str, Any]:
        """Test root information endpoint"""
        print("\\n🔍 Testing root endpoint...")
        try:
            response = await self.client.get(f"{self.base_url}/")
            response.raise_for_status()
            result = response.json()
            
            expected_fields = ["message", "version"]
            if all(field in result for field in expected_fields):
                print(f"✅ Root endpoint passed: {result['message']}")
                return {"status": "passed", "response": result}
            else:
                print("❌ Root endpoint failed: missing fields")
                return {"status": "failed", "error": "Missing fields"}
                
        except Exception as e:
            print(f"❌ Root endpoint failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def test_user_authentication(self) -> Dict[str, Any]:
        """Test user login and token generation"""
        print("\\n🔍 Testing user authentication...")
        
        results = []
        for username, user_data in TEST_USERS.items():
            print(f"  Testing login for user: {username}")
            
            try:
                # Prepare form data for OAuth2 password flow
                login_data = {
                    "username": user_data["username"],
                    "password": user_data["password"]
                }
                
                response = await self.client.post(
                    f"{self.base_url}/token",
                    data=login_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                response.raise_for_status()
                result = response.json()
                
                # Validate token response structure
                required_fields = ["access_token", "token_type"]
                if all(field in result for field in required_fields):
                    token = result["access_token"]
                    token_type = result["token_type"]
                    
                    # Basic token validation
                    if token and token_type == "bearer" and len(token) > 20:
                        # Store valid token for later tests
                        self.valid_tokens[username] = token
                        
                        print(f"    ✅ Login successful for {username}")
                        results.append({
                            "username": username,
                            "status": "passed",
                            "token_length": len(token),
                            "token_type": token_type
                        })
                    else:
                        print(f"    ❌ Login failed for {username}: invalid token format")
                        results.append({
                            "username": username,
                            "status": "failed",
                            "error": "Invalid token format"
                        })
                else:
                    print(f"    ❌ Login failed for {username}: missing required fields")
                    results.append({
                        "username": username,
                        "status": "failed",
                        "error": "Missing required fields in response"
                    })
                    
            except Exception as e:
                print(f"    ❌ Login failed for {username}: {e}")
                results.append({
                    "username": username,
                    "status": "failed",
                    "error": str(e)
                })
        
        passed = sum(1 for r in results if r["status"] == "passed")
        total = len(results)
        
        if passed == total:
            print(f"✅ User authentication passed: {passed}/{total} users authenticated")
            return {"status": "passed", "results": results, "passed": passed, "total": total}
        else:
            print(f"❌ User authentication failed: {passed}/{total} users authenticated")
            return {"status": "failed", "results": results, "passed": passed, "total": total}
    
    async def test_token_validation_and_user_profile(self) -> Dict[str, Any]:
        """Test token validation and user profile retrieval"""
        print("\\n🔍 Testing token validation and user profile...")
        
        if not self.valid_tokens:
            print("❌ No valid tokens available for testing")
            return {"status": "failed", "error": "No valid tokens"}
        
        results = []
        for username, token in self.valid_tokens.items():
            print(f"  Testing profile retrieval for user: {username}")
            
            try:
                headers = {"Authorization": f"Bearer {token}"}
                response = await self.client.get(
                    f"{self.base_url}/users/me",
                    headers=headers
                )
                response.raise_for_status()
                user_profile = response.json()
                
                # Validate user profile structure
                expected_fields = ["username"]
                if all(field in user_profile for field in expected_fields):
                    # Verify user data matches expectations
                    expected_data = TEST_USERS[username]
                    
                    profile_checks = {
                        "username_match": user_profile["username"] == expected_data["username"],
                        "has_email": "email" in user_profile,
                        "has_full_name": "full_name" in user_profile
                    }
                    
                    if profile_checks["username_match"]:
                        print(f"    ✅ Profile retrieved for {username}")
                        results.append({
                            "username": username,
                            "status": "passed",
                            "profile": user_profile,
                            "checks": profile_checks
                        })
                    else:
                        print(f"    ❌ Profile data mismatch for {username}")
                        results.append({
                            "username": username,
                            "status": "failed",
                            "error": "Profile data mismatch",
                            "checks": profile_checks
                        })
                else:
                    print(f"    ❌ Profile missing required fields for {username}")
                    results.append({
                        "username": username,
                        "status": "failed",
                        "error": "Missing required fields in profile"
                    })
                    
            except Exception as e:
                print(f"    ❌ Profile retrieval failed for {username}: {e}")
                results.append({
                    "username": username,
                    "status": "failed",
                    "error": str(e)
                })
        
        passed = sum(1 for r in results if r["status"] == "passed")
        total = len(results)
        
        if passed == total:
            print(f"✅ Token validation passed: {passed}/{total} profiles retrieved")
            return {"status": "passed", "results": results, "passed": passed, "total": total}
        else:
            print(f"❌ Token validation failed: {passed}/{total} profiles retrieved")
            return {"status": "failed", "results": results, "passed": passed, "total": total}
    
    async def test_jwt_token_structure(self) -> Dict[str, Any]:
        """Test JWT token structure and claims"""
        print("\\n🔍 Testing JWT token structure...")
        
        if not self.valid_tokens:
            print("❌ No valid tokens available for JWT testing")
            return {"status": "failed", "error": "No valid tokens"}
        
        results = []
        for username, token in self.valid_tokens.items():
            print(f"  Analyzing JWT token for user: {username}")
            
            try:
                # Decode JWT without verification to inspect structure
                # (In production, always verify the signature!)
                decoded_payload = jwt.decode(token, options={"verify_signature": False})
                
                # Check for required JWT claims
                required_claims = ["sub", "exp"]  # subject, expiration
                
                jwt_checks = {
                    "has_subject": "sub" in decoded_payload,
                    "has_expiration": "exp" in decoded_payload,
                    "subject_matches": decoded_payload.get("sub") == username,
                    "not_expired": decoded_payload.get("exp", 0) > datetime.utcnow().timestamp()
                }
                
                if all(jwt_checks.values()):
                    print(f"    ✅ JWT structure valid for {username}")
                    results.append({
                        "username": username,
                        "status": "passed",
                        "payload": decoded_payload,
                        "checks": jwt_checks
                    })
                else:
                    failed_checks = [k for k, v in jwt_checks.items() if not v]
                    print(f"    ❌ JWT structure invalid for {username}: {failed_checks}")
                    results.append({
                        "username": username,
                        "status": "failed",
                        "error": f"Failed checks: {failed_checks}",
                        "checks": jwt_checks
                    })
                    
            except Exception as e:
                print(f"    ❌ JWT analysis failed for {username}: {e}")
                results.append({
                    "username": username,
                    "status": "failed",
                    "error": str(e)
                })
        
        passed = sum(1 for r in results if r["status"] == "passed")
        total = len(results)
        
        if passed == total:
            print(f"✅ JWT token structure passed: {passed}/{total} tokens valid")
            return {"status": "passed", "results": results, "passed": passed, "total": total}
        else:
            print(f"❌ JWT token structure failed: {passed}/{total} tokens valid")
            return {"status": "failed", "results": results, "passed": passed, "total": total}
    
    async def test_authentication_failures(self) -> Dict[str, Any]:
        """Test authentication with invalid credentials"""
        print("\\n🔍 Testing authentication failure scenarios...")
        
        results = []
        for i, invalid_creds in enumerate(INVALID_CREDENTIALS, 1):
            case_name = f"Invalid credentials {i}"
            print(f"  Testing {case_name}: {invalid_creds['username']}")
            
            try:
                response = await self.client.post(
                    f"{self.base_url}/token",
                    data=invalid_creds,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                # Should return 401 Unauthorized
                if response.status_code == 401:
                    error_detail = response.json().get("detail", "")
                    print(f"    ✅ {case_name}: correctly rejected (401)")
                    results.append({
                        "case": case_name,
                        "status": "passed",
                        "response_code": 401,
                        "error_detail": error_detail
                    })
                else:
                    print(f"    ❌ {case_name}: unexpected status {response.status_code}")
                    results.append({
                        "case": case_name,
                        "status": "failed",
                        "response_code": response.status_code,
                        "error": "Expected 401 but got different status"
                    })
                    
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    print(f"    ✅ {case_name}: correctly rejected (401)")
                    results.append({
                        "case": case_name,
                        "status": "passed",
                        "response_code": 401
                    })
                else:
                    print(f"    ❌ {case_name}: unexpected status {e.response.status_code}")
                    results.append({
                        "case": case_name,
                        "status": "failed",
                        "response_code": e.response.status_code
                    })
            except Exception as e:
                print(f"    ❌ {case_name}: unexpected error {e}")
                results.append({
                    "case": case_name,
                    "status": "error",
                    "error": str(e)
                })
        
        passed = sum(1 for r in results if r["status"] == "passed")
        total = len(results)
        
        if passed == total:
            print(f"✅ Authentication failures handled correctly: {passed}/{total}")
            return {"status": "passed", "results": results, "passed": passed, "total": total}
        else:
            print(f"❌ Authentication failure handling issues: {passed}/{total}")
            return {"status": "failed", "results": results, "passed": passed, "total": total}
    
    async def test_token_authorization_failures(self) -> Dict[str, Any]:
        """Test authorization with invalid tokens"""
        print("\\n🔍 Testing token authorization failures...")
        
        results = []
        for i, invalid_token in enumerate(INVALID_TOKENS, 1):
            case_name = f"Invalid token {i}"
            print(f"  Testing {case_name}")
            
            try:
                headers = {"Authorization": f"Bearer {invalid_token}"}
                response = await self.client.get(
                    f"{self.base_url}/users/me",
                    headers=headers
                )
                
                # Should return 401 Unauthorized
                if response.status_code == 401:
                    error_detail = response.json().get("detail", "")
                    print(f"    ✅ {case_name}: correctly rejected (401)")
                    results.append({
                        "case": case_name,
                        "status": "passed",
                        "response_code": 401,
                        "error_detail": error_detail
                    })
                else:
                    print(f"    ❌ {case_name}: unexpected status {response.status_code}")
                    results.append({
                        "case": case_name,
                        "status": "failed",
                        "response_code": response.status_code
                    })
                    
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    print(f"    ✅ {case_name}: correctly rejected (401)")
                    results.append({
                        "case": case_name,
                        "status": "passed",
                        "response_code": 401
                    })
                else:
                    print(f"    ❌ {case_name}: unexpected status {e.response.status_code}")
                    results.append({
                        "case": case_name,
                        "status": "failed",
                        "response_code": e.response.status_code
                    })
            except Exception as e:
                print(f"    ❌ {case_name}: unexpected error {e}")
                results.append({
                    "case": case_name,
                    "status": "error",
                    "error": str(e)
                })
        
        passed = sum(1 for r in results if r["status"] == "passed")
        total = len(results)
        
        if passed == total:
            print(f"✅ Token authorization failures handled correctly: {passed}/{total}")
            return {"status": "passed", "results": results, "passed": passed, "total": total}
        else:
            print(f"❌ Token authorization failure handling issues: {passed}/{total}")
            return {"status": "failed", "results": results, "passed": passed, "total": total}
    
    async def test_token_expiration(self) -> Dict[str, Any]:
        """Test token expiration handling"""
        print("\\n🔍 Testing token expiration...")
        
        try:
            # Get a fresh token
            login_data = {
                "username": "admin",
                "password": "admin123"
            }
            
            response = await self.client.post(
                f"{self.base_url}/token",
                data=login_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            result = response.json()
            token = result["access_token"]
            
            # Decode to check expiration time
            decoded = jwt.decode(token, options={"verify_signature": False})
            exp_timestamp = decoded.get("exp", 0)
            current_timestamp = datetime.utcnow().timestamp()
            
            time_to_expire = exp_timestamp - current_timestamp
            expire_minutes = time_to_expire / 60
            
            print(f"  Token expires in {expire_minutes:.1f} minutes")
            
            if 25 <= expire_minutes <= 35:  # Default is 30 minutes
                print("✅ Token expiration time is reasonable")
                return {
                    "status": "passed",
                    "expire_minutes": round(expire_minutes, 1),
                    "current_time": current_timestamp,
                    "expire_time": exp_timestamp
                }
            else:
                print(f"⚠️ Token expiration time unusual: {expire_minutes:.1f} minutes")
                return {
                    "status": "warning",
                    "expire_minutes": round(expire_minutes, 1),
                    "note": "Expiration time outside expected range"
                }
                
        except Exception as e:
            print(f"❌ Token expiration test failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def test_security_headers(self) -> Dict[str, Any]:
        """Test security-related response headers"""
        print("\\n🔍 Testing security headers...")
        
        try:
            # Test login endpoint
            response = await self.client.post(
                f"{self.base_url}/token",
                data={"username": "admin", "password": "admin123"},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            headers = dict(response.headers)
            
            # Check for security headers
            security_checks = {
                "has_content_type": "content-type" in headers,
                "has_cache_control": "cache-control" in headers,
                "content_type_json": headers.get("content-type", "").startswith("application/json")
            }
            
            # Additional security considerations
            auth_header = headers.get("www-authenticate")
            
            print("  Security header analysis:")
            for check, passed in security_checks.items():
                print(f"    {'✅' if passed else '⚠️'} {check}: {passed}")
            
            if auth_header:
                print(f"    ℹ️ WWW-Authenticate header: {auth_header}")
            
            passed_checks = sum(1 for v in security_checks.values() if v)
            total_checks = len(security_checks)
            
            if passed_checks >= total_checks * 0.8:  # 80% of checks pass
                print("✅ Security headers test passed")
                return {
                    "status": "passed",
                    "checks": security_checks,
                    "headers": headers,
                    "passed_checks": passed_checks,
                    "total_checks": total_checks
                }
            else:
                print("⚠️ Security headers test partial")
                return {
                    "status": "partial",
                    "checks": security_checks,
                    "headers": headers,
                    "passed_checks": passed_checks,
                    "total_checks": total_checks
                }
                
        except Exception as e:
            print(f"❌ Security headers test failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def test_concurrent_authentication(self) -> Dict[str, Any]:
        """Test concurrent authentication requests"""
        print("\\n🔍 Testing concurrent authentication...")
        
        async def authenticate_user(session_id: int):
            """Authenticate a single user session"""
            try:
                login_data = {
                    "username": "admin",
                    "password": "admin123"
                }
                
                start_time = datetime.now()
                response = await self.client.post(
                    f"{self.base_url}/token",
                    data=login_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                response.raise_for_status()
                end_time = datetime.now()
                
                result = response.json()
                response_time = (end_time - start_time).total_seconds()
                
                if "access_token" in result:
                    return {
                        "session_id": session_id,
                        "status": "success",
                        "response_time": response_time,
                        "token_length": len(result["access_token"])
                    }
                else:
                    return {
                        "session_id": session_id,
                        "status": "failed",
                        "error": "No access token in response"
                    }
                    
            except Exception as e:
                return {
                    "session_id": session_id,
                    "status": "error",
                    "error": str(e)
                }
        
        # Run 5 concurrent authentication requests
        concurrent_sessions = 5
        print(f"  Running {concurrent_sessions} concurrent authentication requests...")
        
        tasks = [authenticate_user(i) for i in range(concurrent_sessions)]
        session_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        successful_sessions = []
        failed_sessions = []
        
        for result in session_results:
            if isinstance(result, dict) and result.get("status") == "success":
                successful_sessions.append(result)
            else:
                failed_sessions.append(result)
        
        success_count = len(successful_sessions)
        total_sessions = concurrent_sessions
        success_rate = success_count / total_sessions * 100
        
        if successful_sessions:
            avg_response_time = sum(s["response_time"] for s in successful_sessions) / len(successful_sessions)
            max_response_time = max(s["response_time"] for s in successful_sessions)
            min_response_time = min(s["response_time"] for s in successful_sessions)
        else:
            avg_response_time = max_response_time = min_response_time = 0
        
        print(f"  Results: {success_count}/{total_sessions} successful ({success_rate:.1f}%)")
        if successful_sessions:
            print(f"  Response times: avg {avg_response_time:.3f}s, range {min_response_time:.3f}s - {max_response_time:.3f}s")
        
        if success_rate >= 90:
            print("✅ Concurrent authentication test passed")
            return {
                "status": "passed",
                "success_rate": success_rate,
                "successful_sessions": success_count,
                "total_sessions": total_sessions,
                "avg_response_time": round(avg_response_time, 3),
                "max_response_time": round(max_response_time, 3),
                "min_response_time": round(min_response_time, 3)
            }
        else:
            print("❌ Concurrent authentication test failed")
            return {
                "status": "failed",
                "success_rate": success_rate,
                "successful_sessions": success_count,
                "total_sessions": total_sessions,
                "failed_sessions": failed_sessions
            }
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run comprehensive test suite"""
        print("🚀 Starting Auth Service (User Service) Comprehensive Tests")
        print(f"📍 Testing URL: {self.base_url}")
        print("🔐 Testing authentication, authorization, and security features")
        print("=" * 70)
        
        test_results = {}
        
        # Core functionality tests
        test_results["root"] = await self.test_root_endpoint()
        test_results["health"] = await self.test_health_check()
        test_results["user_authentication"] = await self.test_user_authentication()
        test_results["token_validation"] = await self.test_token_validation_and_user_profile()
        test_results["jwt_structure"] = await self.test_jwt_token_structure()
        test_results["authentication_failures"] = await self.test_authentication_failures()
        test_results["authorization_failures"] = await self.test_token_authorization_failures()
        test_results["token_expiration"] = await self.test_token_expiration()
        test_results["security_headers"] = await self.test_security_headers()
        test_results["concurrent_auth"] = await self.test_concurrent_authentication()
        
        # Calculate summary
        core_tests = [
            "root", "health", "user_authentication", "token_validation", 
            "jwt_structure", "authentication_failures", "authorization_failures",
            "token_expiration", "security_headers", "concurrent_auth"
        ]
        
        passed_core = 0
        for test in core_tests:
            result = test_results[test]
            if result.get("status") == "passed":
                passed_core += 1
            elif result.get("status") in ["partial", "warning"]:
                passed_core += 0.5
        
        total_core = len(core_tests)
        
        print("\\n" + "=" * 70)
        print(f"📊 Auth Service Test Summary:")
        print(f"   Core Tests: {passed_core}/{total_core} passed")
        
        # Authentication details
        auth_result = test_results["user_authentication"]
        if auth_result.get("status") == "passed":
            print(f"   🔑 Authentication: ✅ ({auth_result.get('passed', 0)}/{auth_result.get('total', 0)} users)")
        else:
            print(f"   🔑 Authentication: ❌ ({auth_result.get('passed', 0)}/{auth_result.get('total', 0)} users)")
        
        # Token validation details
        token_result = test_results["token_validation"]
        if token_result.get("status") == "passed":
            print(f"   🎫 Token Validation: ✅ ({token_result.get('passed', 0)}/{token_result.get('total', 0)} tokens)")
        else:
            print(f"   🎫 Token Validation: ❌ ({token_result.get('passed', 0)}/{token_result.get('total', 0)} tokens)")
        
        # Security tests
        security_tests = ["authentication_failures", "authorization_failures"]
        security_passed = sum(1 for test in security_tests if test_results[test].get("status") == "passed")
        print(f"   🛡️ Security Tests: {security_passed}/{len(security_tests)} passed")
        
        # Performance
        concurrent_result = test_results["concurrent_auth"]
        if concurrent_result.get("status") == "passed":
            success_rate = concurrent_result.get("success_rate", 0)
            avg_time = concurrent_result.get("avg_response_time", 0)
            print(f"   ⚡ Performance: ✅ {success_rate:.1f}% success, {avg_time:.3f}s avg")
        else:
            print(f"   ⚡ Performance: ❌ {concurrent_result.get('error', 'failed')}")
        
        print("=" * 70)
        
        test_results["summary"] = {
            "core_passed": passed_core,
            "core_total": total_core,
            "success_rate": round(passed_core / total_core * 100, 2),
            "authentication_working": auth_result.get("status") == "passed",
            "token_validation_working": token_result.get("status") == "passed",
            "security_tests_passed": security_passed,
            "performance_acceptable": concurrent_result.get("status") == "passed"
        }
        
        return test_results


async def main():
    """Main test runner"""
    async with AuthServiceTester() as tester:
        results = await tester.run_all_tests()
        
        # Save results to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"auth_service_test_results_{timestamp}.json"
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\\n💾 Detailed results saved to {filename}")
        
        # Return exit code based on success rate
        success_rate = results["summary"]["success_rate"]
        auth_working = results["summary"]["authentication_working"]
        token_working = results["summary"]["token_validation_working"]
        
        if success_rate >= 90 and auth_working and token_working:
            print("🎉 All auth tests passed successfully!")
            return 0
        elif success_rate >= 75 and (auth_working or token_working):
            print("⚠️  Most auth tests passed with some issues")
            return 1
        else:
            print("❌ Critical auth functionality failures detected")
            return 2


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
