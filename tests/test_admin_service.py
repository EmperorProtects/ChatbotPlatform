#!/usr/bin/env python3
"""
Test script for Admin Service

Tests all endpoints of the Admin Service including:
- Health check
- System statistics
- Service status monitoring
- Knowledge management
- Error handling
"""

import asyncio
import httpx
import json
from typing import Dict, Any
import os
from datetime import datetime

# Configuration
ADMIN_SERVICE_URL = os.getenv("ADMIN_SERVICE_URL", "http://localhost:8003")
TIMEOUT = httpx.Timeout(60.0, connect=10.0)

class AdminServiceTester:
    def __init__(self, base_url: str = ADMIN_SERVICE_URL):
        self.base_url = base_url
        self.client = None
        
    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=TIMEOUT)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
    
    async def test_health_check(self) -> Dict[str, Any]:
        """Test service health endpoint"""
        print("\n🔍 Testing admin service health check...")
        try:
            response = await self.client.get(f"{self.base_url}/health")
            response.raise_for_status()
            result = response.json()
            
            if result.get("status") == "healthy":
                print("✅ Admin service health check passed")
                return {"status": "passed", "response": result}
            else:
                print("❌ Admin service health check failed")
                return {"status": "failed", "response": result}
                
        except Exception as e:
            print(f"❌ Admin service health check failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def test_root_endpoint(self) -> Dict[str, Any]:
        """Test root endpoint"""
        print("\n🔍 Testing admin service root endpoint...")
        try:
            response = await self.client.get(f"{self.base_url}/")
            response.raise_for_status()
            result = response.json()
            
            if result.get("message") == "Admin Service" and "endpoints" in result:
                print("✅ Admin service root endpoint passed")
                return {"status": "passed", "response": result}
            else:
                print("❌ Admin service root endpoint failed")
                return {"status": "failed", "response": result}
                
        except Exception as e:
            print(f"❌ Admin service root endpoint failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def test_system_stats(self) -> Dict[str, Any]:
        """Test system statistics endpoint"""
        print("\n🔍 Testing system statistics...")
        try:
            response = await self.client.get(f"{self.base_url}/stats")
            response.raise_for_status()
            result = response.json()
            
            required_keys = ["services_status", "knowledge_base_stats", "timestamp"]
            if all(key in result for key in required_keys):
                print("✅ System statistics test passed")
                print(f"   Services tracked: {len(result['services_status'])}")
                return {"status": "passed", "response": result}
            else:
                print("❌ System statistics test failed - missing required keys")
                return {"status": "failed", "response": result}
                
        except Exception as e:
            print(f"❌ System statistics test failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def test_services_status(self) -> Dict[str, Any]:
        """Test services status endpoint"""
        print("\n🔍 Testing services status monitoring...")
        try:
            response = await self.client.get(f"{self.base_url}/services/status")
            response.raise_for_status()
            result = response.json()
            
            expected_services = ["knowledge_service", "ai_service", "bot_service", "auth_service"]
            found_services = list(result.keys())
            
            if len(found_services) >= len(expected_services):
                print("✅ Services status monitoring passed")
                print(f"   Services monitored: {found_services}")
                for service, details in result.items():
                    print(f"   {service}: {details.get('status', 'unknown')}")
                return {"status": "passed", "response": result}
            else:
                print("❌ Services status monitoring failed")
                return {"status": "failed", "response": result}
                
        except Exception as e:
            print(f"❌ Services status monitoring failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def test_knowledge_management(self) -> Dict[str, Any]:
        """Test knowledge management endpoints"""
        print("\n🔍 Testing knowledge management...")
        try:
            # Test adding knowledge item
            test_knowledge = {
                "title": "Admin Test Item",
                "content": "This is a test knowledge item added via admin service",
                "brief_id": "1",
                "language": "en",
                "metadata": {"test": True, "created_by": "admin_test"}
            }
            
            add_response = await self.client.post(
                f"{self.base_url}/knowledge",
                json=test_knowledge
            )
            
            if add_response.status_code == 200:
                print("✅ Knowledge item addition passed")
                add_result = add_response.json()
                
                # Test listing knowledge items
                list_response = await self.client.get(
                    f"{self.base_url}/knowledge",
                    params={"brief_id": "1", "limit": 10}
                )
                
                if list_response.status_code == 200:
                    print("✅ Knowledge listing passed")
                    list_result = list_response.json()
                    
                    return {
                        "status": "passed", 
                        "add_response": add_result,
                        "list_response": list_result,
                        "items_count": len(list_result.get("items", []))
                    }
                else:
                    print("❌ Knowledge listing failed")
                    return {"status": "failed", "error": "Knowledge listing failed"}
            else:
                print("❌ Knowledge item addition failed")
                return {"status": "failed", "error": "Knowledge addition failed"}
                
        except Exception as e:
            print(f"❌ Knowledge management test failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all admin service tests"""
        print("🚀 Starting Admin Service Tests")
        print("=" * 50)
        
        results = {
            "service": "admin_service",
            "timestamp": datetime.utcnow().isoformat(),
            "tests": {}
        }
        
        # Run tests
        test_methods = [
            ("health_check", self.test_health_check),
            ("root_endpoint", self.test_root_endpoint),
            ("system_stats", self.test_system_stats),
            ("services_status", self.test_services_status),
            ("knowledge_management", self.test_knowledge_management)
        ]
        
        for test_name, test_method in test_methods:
            try:
                results["tests"][test_name] = await test_method()
            except Exception as e:
                results["tests"][test_name] = {
                    "status": "failed",
                    "error": f"Test execution failed: {str(e)}"
                }
        
        # Summary
        passed_tests = sum(1 for test in results["tests"].values() if test.get("status") == "passed")
        total_tests = len(results["tests"])
        
        print(f"\n📊 Admin Service Test Summary")
        print("=" * 50)
        print(f"✅ Passed: {passed_tests}/{total_tests}")
        print(f"❌ Failed: {total_tests - passed_tests}/{total_tests}")
        
        results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": f"{(passed_tests/total_tests)*100:.1f}%"
        }
        
        return results

async def main():
    """Main test execution"""
    async with AdminServiceTester() as tester:
        results = await tester.run_all_tests()
        
        # Save results
        filename = f"admin_service_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Results saved to: {filename}")
        
        # Return appropriate exit code
        if results["summary"]["failed_tests"] == 0:
            return 0
        else:
            return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)