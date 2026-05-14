#!/usr/bin/env python3
"""
Test script for Analytics Service

Tests all endpoints of the Analytics Service including:
- Health check
- Event tracking
- Metrics overview
- Channel metrics
- Error handling
"""

import asyncio
import httpx
import json
from typing import Dict, Any
import os
from datetime import datetime, timedelta
import random

# Configuration
ANALYTICS_SERVICE_URL = os.getenv("ANALYTICS_SERVICE_URL", "http://localhost:8004")
TIMEOUT = httpx.Timeout(60.0, connect=10.0)

class AnalyticsServiceTester:
    def __init__(self, base_url: str = ANALYTICS_SERVICE_URL):
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
        print("\n🔍 Testing analytics service health check...")
        try:
            response = await self.client.get(f"{self.base_url}/health")
            response.raise_for_status()
            result = response.json()
            
            if result.get("status") == "healthy":
                print("✅ Analytics service health check passed")
                print(f"   Redis status: {result.get('redis', 'unknown')}")
                return {"status": "passed", "response": result}
            else:
                print("❌ Analytics service health check failed")
                return {"status": "failed", "response": result}
                
        except Exception as e:
            print(f"❌ Analytics service health check failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def test_root_endpoint(self) -> Dict[str, Any]:
        """Test root endpoint"""
        print("\n🔍 Testing analytics service root endpoint...")
        try:
            response = await self.client.get(f"{self.base_url}/")
            response.raise_for_status()
            result = response.json()
            
            if result.get("message") == "Analytics Service" and "endpoints" in result:
                print("✅ Analytics service root endpoint passed")
                return {"status": "passed", "response": result}
            else:
                print("❌ Analytics service root endpoint failed")
                return {"status": "failed", "response": result}
                
        except Exception as e:
            print(f"❌ Analytics service root endpoint failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def test_event_tracking(self) -> Dict[str, Any]:
        """Test event tracking functionality"""
        print("\n🔍 Testing event tracking...")
        try:
            # Create test events
            test_events = [
                {
                    "event_type": "message_received",
                    "user_id": "test_user_001",
                    "channel": "telegram",
                    "metadata": {"message_length": 25, "language": "ru"}
                },
                {
                    "event_type": "message_sent",
                    "user_id": "test_user_001", 
                    "channel": "telegram",
                    "metadata": {"response_length": 150}
                },
                {
                    "event_type": "message_received",
                    "user_id": "test_user_002",
                    "channel": "web",
                    "metadata": {"message_length": 30, "language": "en"}
                }
            ]
            
            event_results = []
            for event in test_events:
                response = await self.client.post(
                    f"{self.base_url}/events",
                    json=event
                )
                
                if response.status_code == 200:
                    result = response.json()
                    event_results.append(result)
                else:
                    print(f"❌ Event tracking failed for {event['event_type']}")
                    return {"status": "failed", "error": f"Failed to track {event['event_type']}"}
            
            print(f"✅ Event tracking passed - tracked {len(event_results)} events")
            return {"status": "passed", "events_tracked": len(event_results), "results": event_results}
                
        except Exception as e:
            print(f"❌ Event tracking test failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def test_overview_metrics(self) -> Dict[str, Any]:
        """Test overview metrics endpoint"""
        print("\n🔍 Testing overview metrics...")
        try:
            response = await self.client.get(f"{self.base_url}/metrics/overview?days=7")
            response.raise_for_status()
            result = response.json()
            
            required_keys = ["total_messages", "unique_users", "channels", "daily_breakdown"]
            if all(key in result for key in required_keys):
                print("✅ Overview metrics test passed")
                print(f"   Total messages: {result.get('total_messages', 0)}")
                print(f"   Unique users: {result.get('unique_users', 0)}")
                print(f"   Channels: {list(result.get('channels', {}).keys())}")
                print(f"   Daily data points: {len(result.get('daily_breakdown', []))}")
                return {"status": "passed", "response": result}
            else:
                print("❌ Overview metrics test failed - missing required keys")
                return {"status": "failed", "response": result}
                
        except Exception as e:
            print(f"❌ Overview metrics test failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def test_channel_metrics(self) -> Dict[str, Any]:
        """Test channel-specific metrics"""
        print("\n🔍 Testing channel metrics...")
        try:
            response = await self.client.get(f"{self.base_url}/metrics/channels")
            response.raise_for_status()
            result = response.json()
            
            print("✅ Channel metrics test passed")
            if result:
                print(f"   Channels with data: {list(result.keys())}")
                for channel, metrics in result.items():
                    print(f"   {channel}: {metrics}")
            else:
                print("   No channel data available (this is normal for a new system)")
            
            return {"status": "passed", "response": result}
                
        except Exception as e:
            print(f"❌ Channel metrics test failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def test_bulk_event_tracking(self) -> Dict[str, Any]:
        """Test bulk event tracking for performance"""
        print("\n🔍 Testing bulk event tracking...")
        try:
            # Generate multiple events quickly
            channels = ["telegram", "web", "whatsapp"]
            event_types = ["message_received", "message_sent", "user_session"]
            
            events_tracked = 0
            start_time = datetime.utcnow()
            
            for i in range(10):
                event = {
                    "event_type": random.choice(event_types),
                    "user_id": f"bulk_test_user_{i % 3}",
                    "channel": random.choice(channels),
                    "metadata": {"bulk_test": True, "sequence": i}
                }
                
                response = await self.client.post(
                    f"{self.base_url}/events",
                    json=event
                )
                
                if response.status_code == 200:
                    events_tracked += 1
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            print(f"✅ Bulk event tracking passed")
            print(f"   Events tracked: {events_tracked}/10")
            print(f"   Duration: {duration:.2f}s")
            print(f"   Rate: {events_tracked/duration:.1f} events/second")
            
            return {
                "status": "passed",
                "events_tracked": events_tracked,
                "duration_seconds": duration,
                "events_per_second": events_tracked/duration
            }
                
        except Exception as e:
            print(f"❌ Bulk event tracking test failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def test_error_handling(self) -> Dict[str, Any]:
        """Test error handling with invalid data"""
        print("\n🔍 Testing error handling...")
        try:
            # Test invalid event data
            invalid_events = [
                {},  # Empty event
                {"event_type": "test"},  # Missing required fields
                {"event_type": "test", "user_id": "test", "channel": ""},  # Empty channel
            ]
            
            error_responses = []
            for invalid_event in invalid_events:
                response = await self.client.post(
                    f"{self.base_url}/events",
                    json=invalid_event
                )
                error_responses.append({
                    "status_code": response.status_code,
                    "event": invalid_event
                })
            
            # Should get error responses for invalid data
            if all(resp["status_code"] >= 400 for resp in error_responses):
                print("✅ Error handling test passed - properly rejected invalid events")
                return {"status": "passed", "error_responses": error_responses}
            else:
                print("❌ Error handling test failed - accepted invalid events")
                return {"status": "failed", "error_responses": error_responses}
                
        except Exception as e:
            print(f"❌ Error handling test failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all analytics service tests"""
        print("🚀 Starting Analytics Service Tests")
        print("=" * 50)
        
        results = {
            "service": "analytics_service",
            "timestamp": datetime.utcnow().isoformat(),
            "tests": {}
        }
        
        # Run tests
        test_methods = [
            ("health_check", self.test_health_check),
            ("root_endpoint", self.test_root_endpoint),
            ("event_tracking", self.test_event_tracking),
            ("overview_metrics", self.test_overview_metrics),
            ("channel_metrics", self.test_channel_metrics),
            ("bulk_event_tracking", self.test_bulk_event_tracking),
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
        
        print(f"\n📊 Analytics Service Test Summary")
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
    async with AnalyticsServiceTester() as tester:
        results = await tester.run_all_tests()
        
        # Save results
        filename = f"analytics_service_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
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
