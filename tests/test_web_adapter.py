#!/usr/bin/env python3
"""
Test script for Web Adapter

Tests all endpoints of the Web Adapter including:
- Health check
- Chat API
- WebSocket functionality
- Static content serving
- Error handling
"""

import asyncio
import httpx
import json
from typing import Dict, Any
import os
from datetime import datetime
import websockets

# Configuration
WEB_ADAPTER_URL = os.getenv("WEB_ADAPTER_URL", "http://localhost:8007")
WEB_ADAPTER_WS = WEB_ADAPTER_URL.replace("http://", "ws://")
TIMEOUT = httpx.Timeout(60.0, connect=10.0)

class WebAdapterTester:
    def __init__(self, base_url: str = WEB_ADAPTER_URL):
        self.base_url = base_url
        self.ws_url = base_url.replace("http://", "ws://")
        self.client = None
        
    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=TIMEOUT)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
    
    async def test_health_check(self) -> Dict[str, Any]:
        """Test service health endpoint"""
        print("\n🔍 Testing web adapter health check...")
        try:
            response = await self.client.get(f"{self.base_url}/health")
            response.raise_for_status()
            result = response.json()
            
            if result.get("status") == "healthy":
                print("✅ Web adapter health check passed")
                print(f"   Connected users: {result.get('connected_users', 0)}")
                return {"status": "passed", "response": result}
            else:
                print("❌ Web adapter health check failed")
                return {"status": "failed", "response": result}
                
        except Exception as e:
            print(f"❌ Web adapter health check failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def test_root_endpoint(self) -> Dict[str, Any]:
        """Test root endpoint"""
        print("\n🔍 Testing web adapter root endpoint...")
        try:
            response = await self.client.get(f"{self.base_url}/")
            response.raise_for_status()
            result = response.json()
            
            if result.get("message") == "Web Adapter" and "endpoints" in result:
                print("✅ Web adapter root endpoint passed")
                print(f"   Available endpoints: {list(result['endpoints'].keys())}")
                return {"status": "passed", "response": result}
            else:
                print("❌ Web adapter root endpoint failed")
                return {"status": "failed", "response": result}
                
        except Exception as e:
            print(f"❌ Web adapter root endpoint failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def test_chat_page(self) -> Dict[str, Any]:
        """Test chat page serving"""
        print("\n🔍 Testing chat page...")
        try:
            response = await self.client.get(f"{self.base_url}/chat")
            response.raise_for_status()
            
            content = response.text
            if "<!DOCTYPE html>" in content and "chat-container" in content:
                print("✅ Chat page test passed")
                print(f"   Content length: {len(content)} characters")
                return {"status": "passed", "content_length": len(content)}
            else:
                print("❌ Chat page test failed - invalid HTML content")
                return {"status": "failed", "error": "Invalid HTML content"}
                
        except Exception as e:
            print(f"❌ Chat page test failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def test_chat_api(self) -> Dict[str, Any]:
        """Test REST chat API"""
        print("\n🔍 Testing chat API...")
        try:
            test_messages = [
                {
                    "message": "Hello, this is a test message",
                    "user_id": "test_web_user_001",
                    "brief_id": "1",
                    "language": "en"
                },
                {
                    "message": "Привет, расскажи о ваших услугах",
                    "user_id": "test_web_user_002", 
                    "brief_id": "1",
                    "language": "ru"
                }
            ]
            
            api_results = []
            for msg in test_messages:
                response = await self.client.post(
                    f"{self.base_url}/api/chat",
                    json=msg
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("status") == "success" and "bot_response" in result:
                        api_results.append({
                            "user_message": msg["message"],
                            "bot_response": result["bot_response"],
                            "language": msg["language"]
                        })
                else:
                    print(f"❌ Chat API failed for message: {msg['message'][:30]}...")
                    return {"status": "failed", "error": f"API returned {response.status_code}"}
            
            print(f"✅ Chat API test passed - processed {len(api_results)} messages")
            for result in api_results:
                print(f"   User ({result['language']}): {result['user_message'][:50]}...")
                print(f"   Bot: {result['bot_response'][:50]}...")
            
            return {"status": "passed", "conversations": api_results}
                
        except Exception as e:
            print(f"❌ Chat API test failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def test_websocket_chat(self) -> Dict[str, Any]:
        """Test WebSocket chat functionality"""
        print("\n🔍 Testing WebSocket chat...")
        try:
            ws_url = f"{self.ws_url}/ws"
            
            # Test messages
            test_messages = [
                {
                    "message": "Hello via WebSocket",
                    "user_id": "ws_test_user_001",
                    "brief_id": "1"
                },
                {
                    "message": "How can you help me?",
                    "user_id": "ws_test_user_001",
                    "brief_id": "1"
                }
            ]
            
            responses = []
            
            async with websockets.connect(ws_url) as websocket:
                print("   WebSocket connection established")
                
                for msg in test_messages:
                    # Send message
                    await websocket.send(json.dumps(msg))
                    print(f"   Sent: {msg['message']}")
                    
                    # Receive response (with timeout)
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                        response_data = json.loads(response)
                        responses.append({
                            "user_message": msg["message"],
                            "bot_response": response_data.get("message", "No response")
                        })
                        print(f"   Received: {response_data.get('message', 'No message')[:50]}...")
                    except asyncio.TimeoutError:
                        print(f"   ⚠️  Timeout waiting for response to: {msg['message']}")
                        responses.append({
                            "user_message": msg["message"],
                            "bot_response": "TIMEOUT"
                        })
            
            if responses:
                print(f"✅ WebSocket chat test passed - {len(responses)} exchanges")
                return {"status": "passed", "exchanges": responses}
            else:
                print("❌ WebSocket chat test failed - no responses")
                return {"status": "failed", "error": "No responses received"}
                
        except Exception as e:
            print(f"❌ WebSocket chat test failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def test_concurrent_connections(self) -> Dict[str, Any]:
        """Test multiple concurrent connections"""
        print("\n🔍 Testing concurrent WebSocket connections...")
        try:
            async def single_connection(user_id: str):
                ws_url = f"{self.ws_url}/ws"
                try:
                    async with websockets.connect(ws_url) as websocket:
                        message = {
                            "message": f"Concurrent test from {user_id}",
                            "user_id": user_id,
                            "brief_id": "1"
                        }
                        
                        await websocket.send(json.dumps(message))
                        response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                        response_data = json.loads(response)
                        
                        return {
                            "user_id": user_id,
                            "success": True,
                            "response": response_data.get("message", "")[:100]
                        }
                except Exception as e:
                    return {
                        "user_id": user_id,
                        "success": False,
                        "error": str(e)
                    }
            
            # Test with 3 concurrent connections
            tasks = [
                single_connection(f"concurrent_user_{i}")
                for i in range(3)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful_connections = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
            
            print(f"✅ Concurrent connections test completed")
            print(f"   Successful connections: {successful_connections}/3")
            
            return {
                "status": "passed" if successful_connections >= 2 else "failed",
                "successful_connections": successful_connections,
                "total_attempted": 3,
                "results": results
            }
                
        except Exception as e:
            print(f"❌ Concurrent connections test failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def test_error_handling(self) -> Dict[str, Any]:
        """Test error handling with invalid requests"""
        print("\n🔍 Testing error handling...")
        try:
            # Test invalid chat API requests
            invalid_requests = [
                {},  # Empty request
                {"message": ""},  # Empty message
                {"user_id": "test"},  # Missing message
                {"message": "test", "brief_id": "invalid_brief"}  # Invalid brief
            ]
            
            error_responses = []
            for invalid_req in invalid_requests:
                response = await self.client.post(
                    f"{self.base_url}/api/chat",
                    json=invalid_req
                )
                error_responses.append({
                    "request": invalid_req,
                    "status_code": response.status_code,
                    "handled_gracefully": response.status_code >= 400
                })
            
            graceful_errors = sum(1 for resp in error_responses if resp["handled_gracefully"])
            
            print(f"✅ Error handling test passed")
            print(f"   Gracefully handled errors: {graceful_errors}/{len(error_responses)}")
            
            return {
                "status": "passed",
                "graceful_errors": graceful_errors,
                "total_errors": len(error_responses),
                "error_responses": error_responses
            }
                
        except Exception as e:
            print(f"❌ Error handling test failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all web adapter tests"""
        print("🚀 Starting Web Adapter Tests")
        print("=" * 50)
        
        results = {
            "service": "web_adapter",
            "timestamp": datetime.utcnow().isoformat(),
            "tests": {}
        }
        
        # Run tests
        test_methods = [
            ("health_check", self.test_health_check),
            ("root_endpoint", self.test_root_endpoint),
            ("chat_page", self.test_chat_page),
            ("chat_api", self.test_chat_api),
            ("websocket_chat", self.test_websocket_chat),
            ("concurrent_connections", self.test_concurrent_connections),
            ("error_handling", self.test_error_handling)
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
        
        print(f"\n📊 Web Adapter Test Summary")
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
    async with WebAdapterTester() as tester:
        results = await tester.run_all_tests()
        
        # Save results
        filename = f"web_adapter_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
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