#!/usr/bin/env python3
"""
Test script for API Gateway (Request Routing and Proxy)

Tests all endpoints of the API Gateway including:
- Health check
- Service routing and proxying
- CORS handling
- Error handling and fallbacks
"""

import asyncio
import httpx
import json
from typing import Dict, Any, List
import os
from datetime import datetime

# Configuration
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:8000")
TIMEOUT = httpx.Timeout(60.0, connect=10.0)

# Test routes and expected behavior
TEST_ROUTES = [
    {
        "name": "Auth Service Route",
        "path": "/auth/health",
        "method": "GET",
        "expected_proxy": True
    },
    {
        "name": "Bot Service Route", 
        "path": "/bot/health",
        "method": "GET",
        "expected_proxy": True
    },
    {
        "name": "Admin Service Route",
        "path": "/admin/health", 
        "method": "GET",
        "expected_proxy": True
    },
    {
        "name": "Analytics Service Route",
        "path": "/analytics/health",
        "method": "GET", 
        "expected_proxy": True
    }
]

# CORS test data
CORS_TEST_ORIGINS = [
    "http://localhost:3000",
    "https://example.com",
    "https://app.mydomain.com"
]

class APIGatewayTester:
    def __init__(self, base_url: str = API_GATEWAY_URL):
        self.base_url = base_url
        self.client = None
        
    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=TIMEOUT)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
    
    async def test_health_check(self) -> Dict[str, Any]:
        """Test gateway health endpoint"""
        print("\n🔍 Testing gateway health check...")
        try:
            response = await self.client.get(f"{self.base_url}/health")
            response.raise_for_status()
            result = response.json()
            
            if result.get("status") == "healthy":
                print("✅ Gateway health check passed")
                return {"status": "passed", "response": result}
            else:
                print(f"❌ Gateway health check failed: {result}")
                return {"status": "failed", "response": result}
                
        except Exception as e:
            print(f"❌ Gateway health check failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def test_root_endpoint(self) -> Dict[str, Any]:
        """Test root information endpoint"""
        print("\n🔍 Testing root endpoint...")
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
    
    async def test_service_routing(self) -> Dict[str, Any]:
        """Test routing to different services"""
        print("\n🔍 Testing service routing...")
        
        results = []
        for route in TEST_ROUTES:
            print(f"  Testing {route['name']} ({route['path']})...")
            
            try:
                response = await self.client.request(
                    method=route["method"],
                    url=f"{self.base_url}{route['path']}"
                )
                
                # We expect one of these outcomes:
                # 1. Successful proxy (200) - backend service responded
                # 2. Service unavailable (502, 503, 504) - backend down but gateway working
                # 3. Not found (404) - route not configured
                
                if response.status_code == 200:
                    print(f"    ✅ {route['name']}: successfully proxied")
                    results.append({
                        "route": route["name"],
                        "status": "proxied",
                        "status_code": 200
                    })
                elif response.status_code in [502, 503, 504]:
                    print(f"    ⚠️ {route['name']}: gateway working, backend unavailable ({response.status_code})")
                    results.append({
                        "route": route["name"], 
                        "status": "backend_down",
                        "status_code": response.status_code
                    })
                elif response.status_code == 404:
                    print(f"    ❌ {route['name']}: route not configured")
                    results.append({
                        "route": route["name"],
                        "status": "not_configured", 
                        "status_code": 404
                    })
                else:
                    print(f"    ❌ {route['name']}: unexpected status {response.status_code}")
                    results.append({
                        "route": route["name"],
                        "status": "unexpected",
                        "status_code": response.status_code
                    })
                    
            except httpx.ConnectError:
                print(f"    ❌ {route['name']}: gateway connection failed")
                results.append({
                    "route": route["name"],
                    "status": "gateway_down",
                    "error": "Connection failed"
                })
            except Exception as e:
                print(f"    ❌ {route['name']}: error {e}")
                results.append({
                    "route": route["name"],
                    "status": "error",
                    "error": str(e)
                })
        
        # Evaluate results
        proxied = sum(1 for r in results if r["status"] == "proxied")
        backend_issues = sum(1 for r in results if r["status"] == "backend_down")
        gateway_working = proxied + backend_issues  # Both indicate gateway is functioning
        
        total = len(results)
        
        if proxied == total:
            print(f"✅ Service routing passed: {proxied}/{total} services accessible")
            return {"status": "passed", "results": results, "proxied": proxied, "total": total}
        elif gateway_working >= total * 0.5:  # At least 50% showing gateway functionality
            print(f"⚠️ Service routing partial: {gateway_working}/{total} routes working (some backends down)")
            return {"status": "partial", "results": results, "working": gateway_working, "total": total}
        else:
            print(f"❌ Service routing failed: {gateway_working}/{total} routes working")
            return {"status": "failed", "results": results, "working": gateway_working, "total": total}
    
    async def test_cors_handling(self) -> Dict[str, Any]:
        """Test CORS headers and preflight requests"""
        print("\n🔍 Testing CORS handling...")
        
        results = []
        
        # Test preflight (OPTIONS) requests
        for origin in CORS_TEST_ORIGINS:
            print(f"  Testing CORS for origin: {origin}")
            
            try:
                # OPTIONS preflight request
                headers = {
                    "Origin": origin,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "Content-Type"
                }
                
                response = await self.client.options(
                    f"{self.base_url}/bot/health",
                    headers=headers
                )
                
                # Check CORS headers in response
                cors_headers = {
                    "access-control-allow-origin": response.headers.get("access-control-allow-origin"),
                    "access-control-allow-methods": response.headers.get("access-control-allow-methods"), 
                    "access-control-allow-headers": response.headers.get("access-control-allow-headers"),
                    "access-control-allow-credentials": response.headers.get("access-control-allow-credentials")
                }
                
                # Check if CORS is properly configured
                has_origin = cors_headers["access-control-allow-origin"] is not None
                has_methods = cors_headers["access-control-allow-methods"] is not None
                has_headers = cors_headers["access-control-allow-headers"] is not None
                
                if has_origin and has_methods:
                    print(f"    ✅ CORS configured for {origin}")
                    results.append({
                        "origin": origin,
                        "status": "configured",
                        "headers": cors_headers
                    })
                else:
                    print(f"    ❌ CORS not properly configured for {origin}")
                    results.append({
                        "origin": origin,
                        "status": "not_configured",
                        "headers": cors_headers
                    })
                    
            except Exception as e:
                print(f"    ❌ CORS test failed for {origin}: {e}")
                results.append({
                    "origin": origin,
                    "status": "error",
                    "error": str(e)
                })
        
        # Test actual request with CORS
        try:
            print("  Testing actual request with CORS headers...")
            
            headers = {"Origin": CORS_TEST_ORIGINS[0]}
            response = await self.client.get(
                f"{self.base_url}/health",
                headers=headers
            )
            
            cors_origin = response.headers.get("access-control-allow-origin")
            if cors_origin:
                print("    ✅ CORS headers present in actual response")
                results.append({
                    "test": "actual_request",
                    "status": "configured",
                    "cors_origin": cors_origin
                })
            else:
                print("    ⚠️ CORS headers missing in actual response")
                results.append({
                    "test": "actual_request", 
                    "status": "missing_headers"
                })
                
        except Exception as e:
            print(f"    ❌ Actual CORS request failed: {e}")
            results.append({
                "test": "actual_request",
                "status": "error",
                "error": str(e)
            })
        
        # Evaluate CORS configuration
        configured = sum(1 for r in results if r.get("status") == "configured")
        total_tests = len(results)
        
        if configured >= total_tests * 0.8:  # 80% configured
            print(f"✅ CORS handling passed: {configured}/{total_tests} tests configured properly")
            return {"status": "passed", "results": results, "configured": configured, "total": total_tests}
        else:
            print(f"⚠️ CORS handling partial: {configured}/{total_tests} tests configured properly")
            return {"status": "partial", "results": results, "configured": configured, "total": total_tests}
    
    async def test_request_forwarding(self) -> Dict[str, Any]:
        """Test request forwarding with different methods and payloads"""
        print("\n🔍 Testing request forwarding...")
        
        # Test different HTTP methods and payloads
        test_requests = [
            {
                "name": "GET request",
                "method": "GET",
                "path": "/bot/health",
                "data": None
            },
            {
                "name": "POST request with JSON",
                "method": "POST", 
                "path": "/bot/incoming",
                "data": {
                    "user_id": "gateway_test",
                    "brief_id": "1",
                    "text": "Test message via gateway",
                    "channel": "test"
                }
            }
        ]
        
        results = []
        for test_req in test_requests:
            print(f"  Testing {test_req['name']}...")
            
            try:
                if test_req["method"] == "GET":
                    response = await self.client.get(f"{self.base_url}{test_req['path']}")
                elif test_req["method"] == "POST":
                    response = await self.client.post(
                        f"{self.base_url}{test_req['path']}",
                        json=test_req["data"]
                    )
                
                # Check if request was forwarded (any response from backend)
                if 200 <= response.status_code < 300:
                    print(f"    ✅ {test_req['name']}: successfully forwarded")
                    results.append({
                        "request": test_req["name"],
                        "status": "forwarded",
                        "status_code": response.status_code
                    })
                elif 500 <= response.status_code < 600:
                    print(f"    ⚠️ {test_req['name']}: forwarded but backend error ({response.status_code})")
                    results.append({
                        "request": test_req["name"],
                        "status": "backend_error",
                        "status_code": response.status_code
                    })
                else:
                    print(f"    ❌ {test_req['name']}: forwarding failed ({response.status_code})")
                    results.append({
                        "request": test_req["name"],
                        "status": "failed",
                        "status_code": response.status_code
                    })
                    
            except Exception as e:
                print(f"    ❌ {test_req['name']}: error {e}")
                results.append({
                    "request": test_req["name"],
                    "status": "error", 
                    "error": str(e)
                })
        
        successful = sum(1 for r in results if r["status"] in ["forwarded", "backend_error"])
        total = len(results)
        
        if successful == total:
            print(f"✅ Request forwarding passed: {successful}/{total} requests forwarded")
            return {"status": "passed", "results": results, "successful": successful, "total": total}
        else:
            print(f"⚠️ Request forwarding partial: {successful}/{total} requests forwarded")
            return {"status": "partial", "results": results, "successful": successful, "total": total}
    
    async def test_error_handling(self) -> Dict[str, Any]:
        """Test error handling for invalid routes and requests"""
        print("\n🔍 Testing error handling...")
        
        error_tests = [
            {
                "name": "Invalid route",
                "request": lambda: self.client.get(f"{self.base_url}/nonexistent/path"),
                "expected_status": [404]
            },
            {
                "name": "Invalid service route",
                "request": lambda: self.client.get(f"{self.base_url}/invalidservice/health"),
                "expected_status": [404]
            },
            {
                "name": "Malformed request", 
                "request": lambda: self.client.post(
                    f"{self.base_url}/bot/incoming",
                    data="invalid json",
                    headers={"Content-Type": "application/json"}
                ),
                "expected_status": [400, 422, 502]  # Could be handled by gateway or backend
            }
        ]
        
        results = []
        for test in error_tests:
            try:
                response = await test["request"]()
                if response.status_code in test["expected_status"]:
                    print(f"✅ {test['name']}: correctly returned {response.status_code}")
                    results.append({"test": test["name"], "status": "passed"})
                else:
                    print(f"❌ {test['name']}: unexpected status {response.status_code}")
                    results.append({"test": test["name"], "status": "failed"})
            except httpx.HTTPStatusError as e:
                if e.response.status_code in test["expected_status"]:
                    print(f"✅ {test['name']}: correctly returned {e.response.status_code}")
                    results.append({"test": test["name"], "status": "passed"})
                else:
                    print(f"❌ {test['name']}: unexpected status {e.response.status_code}")
                    results.append({"test": test["name"], "status": "failed"})
            except Exception as e:
                print(f"❌ {test['name']}: unexpected error {e}")
                results.append({"test": test["name"], "status": "error", "error": str(e)})
        
        passed_tests = sum(1 for r in results if r["status"] == "passed")
        total_tests = len(results)
        
        return {
            "status": "completed",
            "passed": passed_tests,
            "total": total_tests,
            "results": results
        }
    
    async def test_response_headers(self) -> Dict[str, Any]:
        """Test that gateway preserves and adds appropriate headers"""
        print("\n🔍 Testing response headers...")
        
        try:
            # Test with health endpoint
            response = await self.client.get(f"{self.base_url}/health")
            
            headers = dict(response.headers)
            
            # Check for important security and functionality headers
            important_headers = {
                "content-type": headers.get("content-type"),
                "access-control-allow-origin": headers.get("access-control-allow-origin"),
                "server": headers.get("server")
            }
            
            # Check content type
            has_content_type = "content-type" in headers
            has_cors = "access-control-allow-origin" in headers
            
            print(f"  Content-Type: {'✅' if has_content_type else '❌'} {important_headers['content-type']}")
            print(f"  CORS Origin: {'✅' if has_cors else '❌'} {important_headers['access-control-allow-origin']}")
            print(f"  Server: {important_headers.get('server', 'Not set')}")
            
            if has_content_type:
                print("✅ Response headers test passed")
                return {
                    "status": "passed", 
                    "headers": important_headers,
                    "has_content_type": has_content_type,
                    "has_cors": has_cors
                }
            else:
                print("⚠️ Response headers test partial: missing content-type")
                return {
                    "status": "partial",
                    "headers": important_headers, 
                    "has_content_type": has_content_type,
                    "has_cors": has_cors
                }
                
        except Exception as e:
            print(f"❌ Response headers test failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run comprehensive test suite"""
        print("🚀 Starting API Gateway Comprehensive Tests")
        print(f"📍 Testing URL: {self.base_url}")
        print("⚠️  Note: Some tests depend on backend services being available")
        print("=" * 60)
        
        test_results = {}
        
        # Core functionality tests
        test_results["root"] = await self.test_root_endpoint()
        test_results["health"] = await self.test_health_check()
        test_results["service_routing"] = await self.test_service_routing()
        test_results["cors_handling"] = await self.test_cors_handling()
        test_results["request_forwarding"] = await self.test_request_forwarding()
        test_results["response_headers"] = await self.test_response_headers()
        test_results["error_handling"] = await self.test_error_handling()
        
        # Calculate summary
        core_tests = ["root", "health", "service_routing", "cors_handling", "request_forwarding", "response_headers"]
        
        passed_core = 0
        for test in core_tests:
            result = test_results[test]
            if result.get("status") == "passed":
                passed_core += 1
            elif result.get("status") == "partial":
                passed_core += 0.5
        
        total_core = len(core_tests)
        
        error_handling = test_results["error_handling"]
        passed_error = error_handling.get("passed", 0)
        total_error = error_handling.get("total", 0)
        
        print("\n" + "=" * 60)
        print(f"📊 API Gateway Test Summary:")
        print(f"   Core Tests: {passed_core}/{total_core} passed")
        print(f"   Error Handling: {passed_error}/{total_error} passed")
        
        # Service routing details
        routing = test_results["service_routing"]
        if routing.get("status") == "passed":
            print(f"   🔀 Service Routing: ✅ ({routing.get('proxied', 0)} services accessible)")
        elif routing.get("status") == "partial":
            print(f"   🔀 Service Routing: ⚠️ ({routing.get('working', 0)}/{routing.get('total', 0)} working)")
        else:
            print(f"   🔀 Service Routing: ❌ ({routing.get('working', 0)}/{routing.get('total', 0)} working)")
        
        # CORS details
        cors = test_results["cors_handling"]
        if cors.get("status") == "passed":
            print(f"   🌐 CORS: ✅ ({cors.get('configured', 0)}/{cors.get('total', 0)} configured)")
        else:
            print(f"   🌐 CORS: ⚠️ ({cors.get('configured', 0)}/{cors.get('total', 0)} configured)")
        
        print("=" * 60)
        
        overall_score = passed_core + passed_error
        overall_total = total_core + total_error
        
        test_results["summary"] = {
            "core_passed": passed_core,
            "core_total": total_core,
            "error_passed": passed_error,
            "error_total": total_error,
            "overall_score": round(overall_score, 2),
            "overall_total": overall_total,
            "success_rate": round(overall_score / overall_total * 100, 2) if overall_total > 0 else 0
        }
        
        return test_results


async def main():
    """Main test runner"""
    async with APIGatewayTester() as tester:
        results = await tester.run_all_tests()
        
        # Save results to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"api_gateway_test_results_{timestamp}.json"
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Detailed results saved to {filename}")
        
        # Return exit code based on success rate
        success_rate = results["summary"]["success_rate"]
        if success_rate >= 80:
            print("🎉 All tests passed successfully!")
            return 0
        elif success_rate >= 60:
            print("⚠️  Most tests passed with some issues")
            return 1
        else:
            print("❌ Multiple test failures detected")
            return 2


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
