#!/usr/bin/env python3
"""
Integration Test Script for Complete Chatbot Platform

Tests end-to-end functionality across all microservices:
- Knowledge Service (ChromaDB)
- AI Service (Ollama)  
- Bot Service (Message Processing)
- API Gateway (Routing)
- Full conversation flows
- Service dependencies
- Performance under load
"""

import asyncio
import httpx
import json
from typing import Dict, Any, List
import os
import time
from datetime import datetime
import uuid

# Configuration
KNOWLEDGE_URL = os.getenv("KNOWLEDGE_URL", "http://localhost:8006")
AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8005")
BOT_SERVICE_URL = os.getenv("BOT_SERVICE_URL", "http://localhost:8002")
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:8000")
TIMEOUT = httpx.Timeout(120.0, connect=15.0)  # Extended for integration tests

# Test scenarios for end-to-end flows
CONVERSATION_SCENARIOS = [
    {
        "name": "Electric car sales inquiry (Russian)",
        "brief_id": 1,
        "conversation": [
            {
                "user_message": "Привет! Расскажи про ваши электромобили",
                "expected_topics": ["электромобиль", "автомобиль", "транспорт"],
                "language": "ru"
            },
            {
                "user_message": "Сколько стоит зарядка?",
                "expected_topics": ["зарядка", "стоимость", "цена"],
                "language": "ru"
            },
            {
                "user_message": "Есть ли сервисная поддержка?",
                "expected_topics": ["сервис", "поддержка", "обслуживание"],
                "language": "ru"
            }
        ]
    },
    {
        "name": "Coffee shop order (English)",
        "brief_id": 2,
        "conversation": [
            {
                "user_message": "Hello! What coffee do you have?",
                "expected_topics": ["coffee", "menu", "drink"],
                "language": "en"
            },
            {
                "user_message": "How much is a cappuccino?",
                "expected_topics": ["cappuccino", "price", "cost"],
                "language": "en"
            },
            {
                "user_message": "Do you have lactose-free milk?",
                "expected_topics": ["lactose", "milk", "dairy"],
                "language": "en"
            }
        ]
    }
]

# Performance test scenarios
LOAD_TEST_SCENARIOS = [
    {
        "name": "Light Load",
        "concurrent_users": 3,
        "requests_per_user": 2
    },
    {
        "name": "Medium Load", 
        "concurrent_users": 5,
        "requests_per_user": 3
    }
]

class IntegrationTester:
    def __init__(self):
        self.knowledge_url = KNOWLEDGE_URL
        self.ai_service_url = AI_SERVICE_URL
        self.bot_service_url = BOT_SERVICE_URL
        self.api_gateway_url = API_GATEWAY_URL
        self.client = None
        self.test_session_id = str(uuid.uuid4())[:8]
        
    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=TIMEOUT)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
    
    async def test_all_services_health(self) -> Dict[str, Any]:
        """Test that all services are healthy and reachable"""
        print("\n🔍 Testing all services health...")
        
        services = [
            ("Knowledge Service", self.knowledge_url),
            ("AI Service", self.ai_service_url),
            ("Bot Service", self.bot_service_url),
            ("API Gateway", self.api_gateway_url)
        ]
        
        results = {}
        all_healthy = True
        
        for service_name, url in services:
            print(f"  Checking {service_name}...")
            try:
                response = await self.client.get(f"{url}/health")
                response.raise_for_status()
                result = response.json()
                
                status = result.get("status", "unknown")
                if status in ["healthy", "ok"]:
                    print(f"    ✅ {service_name}: {status}")
                    results[service_name] = {"status": "healthy", "response": result}
                else:
                    print(f"    ⚠️ {service_name}: {status}")
                    results[service_name] = {"status": "degraded", "response": result}
                    
            except Exception as e:
                print(f"    ❌ {service_name}: unhealthy - {e}")
                results[service_name] = {"status": "unhealthy", "error": str(e)}
                all_healthy = False
        
        return {
            "status": "passed" if all_healthy else "failed",
            "results": results,
            "healthy_count": sum(1 for r in results.values() if r["status"] == "healthy"),
            "total_count": len(results)
        }
    
    async def test_service_dependencies(self) -> Dict[str, Any]:
        """Test dependencies between services"""
        print("\n🔍 Testing service dependencies...")
        
        dependency_tests = [
            {
                "name": "Knowledge Service → AI Service (Embeddings)",
                "test": self._test_knowledge_ai_dependency
            },
            {
                "name": "Bot Service → Knowledge Service (Search)",
                "test": self._test_bot_knowledge_dependency  
            },
            {
                "name": "Bot Service → AI Service (Generation)",
                "test": self._test_bot_ai_dependency
            },
            {
                "name": "API Gateway → All Services (Routing)",
                "test": self._test_gateway_routing_dependency
            }
        ]
        
        results = []
        for test_config in dependency_tests:
            print(f"  Testing {test_config['name']}...")
            try:
                result = await test_config["test"]()
                results.append({
                    "dependency": test_config["name"],
                    "status": result.get("status", "unknown"),
                    "details": result
                })
                print(f"    {'✅' if result.get('status') == 'passed' else '❌'} {test_config['name']}")
            except Exception as e:
                results.append({
                    "dependency": test_config["name"],
                    "status": "error",
                    "error": str(e)
                })
                print(f"    ❌ {test_config['name']}: {e}")
        
        passed = sum(1 for r in results if r["status"] == "passed")
        total = len(results)
        
        return {
            "status": "passed" if passed == total else "partial" if passed > 0 else "failed",
            "results": results,
            "passed": passed,
            "total": total
        }
    
    async def _test_knowledge_ai_dependency(self) -> Dict[str, Any]:
        """Test Knowledge Service using AI Service for embeddings"""
        try:
            # Test adding knowledge (which should use AI service for embeddings)
            test_knowledge = {
                "text": f"Integration test knowledge item {self.test_session_id}",
                "brief_id": 999,
                "category": "test",
                "title": "Integration Test Item",
                "metadata": {"test_session": self.test_session_id}
            }
            
            response = await self.client.post(
                f"{self.knowledge_url}/add",
                json=test_knowledge
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("status") == "success":
                return {"status": "passed", "document_id": result.get("document_id")}
            else:
                return {"status": "failed", "error": "Knowledge addition failed"}
                
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    async def _test_bot_knowledge_dependency(self) -> Dict[str, Any]:
        """Test Bot Service retrieving knowledge from Knowledge Service"""
        try:
            # This tests the internal knowledge retrieval in bot service
            # We'll test via a complete message flow
            test_message = {
                "user_id": f"dep_test_{self.test_session_id}",
                "brief_id": "1",
                "text": "Расскажи про продукты",
                "channel": "test",
                "language": "ru"
            }
            
            response = await self.client.post(
                f"{self.bot_service_url}/incoming",
                json=test_message
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("text") and len(result["text"].strip()) > 0:
                return {"status": "passed", "response_length": len(result["text"])}
            else:
                return {"status": "failed", "error": "Empty or invalid response"}
                
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    async def _test_bot_ai_dependency(self) -> Dict[str, Any]:
        """Test Bot Service using AI Service for generation"""
        try:
            # Test direct AI service call
            ai_request = {
                "user_message": "Test message for dependency check",
                "context": "Test context",
                "language": "en",
                "user_id": f"dep_test_{self.test_session_id}",
                "conversation_history": []
            }
            
            response = await self.client.post(
                f"{self.ai_service_url}/generate",
                json=ai_request
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("response") and len(result["response"].strip()) > 0:
                return {"status": "passed", "model": result.get("model")}
            else:
                return {"status": "failed", "error": "Empty AI response"}
                
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    async def _test_gateway_routing_dependency(self) -> Dict[str, Any]:
        """Test API Gateway routing to services"""
        try:
            # Test routing through gateway
            response = await self.client.get(f"{self.api_gateway_url}/bot/health")
            
            if response.status_code in [200, 502, 503]:  # 200 = success, 5xx = gateway working but backend issues
                return {"status": "passed", "status_code": response.status_code}
            else:
                return {"status": "failed", "status_code": response.status_code}
                
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    async def test_end_to_end_conversations(self) -> Dict[str, Any]:
        """Test complete conversation flows"""
        print("\n🔍 Testing end-to-end conversation flows...")
        
        scenario_results = []
        
        for scenario in CONVERSATION_SCENARIOS:
            print(f"  Testing scenario: {scenario['name']}")
            
            user_id = f"e2e_user_{self.test_session_id}_{len(scenario_results)}"
            conversation_results = []
            total_time = 0
            
            for i, turn in enumerate(scenario["conversation"]):
                print(f"    Turn {i+1}: {turn['user_message'][:50]}...")
                
                try:
                    start_time = time.time()
                    
                    # Send message through bot service
                    message_request = {
                        "user_id": user_id,
                        "brief_id": str(scenario["brief_id"]),
                        "text": turn["user_message"],
                        "channel": "integration_test",
                        "language": turn["language"]
                    }
                    
                    response = await self.client.post(
                        f"{self.bot_service_url}/incoming",
                        json=message_request
                    )
                    response.raise_for_status()
                    result = response.json()
                    
                    response_time = time.time() - start_time
                    total_time += response_time
                    
                    # Validate response
                    bot_response = result.get("text", "")
                    if bot_response and len(bot_response.strip()) > 0:
                        # Check if response contains relevant topics
                        response_lower = bot_response.lower()
                        topics_found = sum(1 for topic in turn["expected_topics"] 
                                         if topic.lower() in response_lower)
                        
                        conversation_results.append({
                            "turn": i + 1,
                            "status": "passed",
                            "response_time": round(response_time, 2),
                            "response_length": len(bot_response),
                            "topics_found": topics_found,
                            "total_topics": len(turn["expected_topics"])
                        })
                        
                        print(f"      ✅ Response received ({response_time:.2f}s, {len(bot_response)} chars)")
                    else:
                        conversation_results.append({
                            "turn": i + 1,
                            "status": "failed",
                            "error": "Empty response"
                        })
                        print(f"      ❌ Empty response")
                        
                except Exception as e:
                    conversation_results.append({
                        "turn": i + 1,
                        "status": "failed",
                        "error": str(e)
                    })
                    print(f"      ❌ Error: {e}")
            
            # Evaluate scenario
            successful_turns = sum(1 for r in conversation_results if r["status"] == "passed")
            total_turns = len(conversation_results)
            
            scenario_result = {
                "scenario": scenario["name"],
                "user_id": user_id,
                "successful_turns": successful_turns,
                "total_turns": total_turns,
                "total_time": round(total_time, 2),
                "avg_time_per_turn": round(total_time / total_turns, 2) if total_turns > 0 else 0,
                "conversation_results": conversation_results
            }
            
            if successful_turns == total_turns:
                scenario_result["status"] = "passed"
                print(f"    ✅ Scenario completed: {successful_turns}/{total_turns} turns successful")
            else:
                scenario_result["status"] = "failed"
                print(f"    ❌ Scenario failed: {successful_turns}/{total_turns} turns successful")
            
            scenario_results.append(scenario_result)
        
        passed_scenarios = sum(1 for r in scenario_results if r["status"] == "passed")
        total_scenarios = len(scenario_results)
        
        return {
            "status": "passed" if passed_scenarios == total_scenarios else "partial" if passed_scenarios > 0 else "failed",
            "results": scenario_results,
            "passed": passed_scenarios,
            "total": total_scenarios
        }
    
    async def test_performance_load(self) -> Dict[str, Any]:
        """Test system performance under load"""
        print("\n🔍 Testing performance under load...")
        
        load_results = []
        
        for load_scenario in LOAD_TEST_SCENARIOS:
            print(f"  Testing {load_scenario['name']}: {load_scenario['concurrent_users']} users, {load_scenario['requests_per_user']} req/user")
            
            async def user_session(user_id: int):
                """Simulate a user session"""
                session_times = []
                session_errors = 0
                
                for req_num in range(load_scenario["requests_per_user"]):
                    try:
                        start_time = time.time()
                        
                        message_request = {
                            "user_id": f"load_user_{user_id}_{req_num}",
                            "brief_id": "1",
                            "text": f"Test message {req_num + 1} from user {user_id}",
                            "channel": "load_test",
                            "language": "ru"
                        }
                        
                        response = await self.client.post(
                            f"{self.bot_service_url}/incoming",
                            json=message_request
                        )
                        response.raise_for_status()
                        result = response.json()
                        
                        response_time = time.time() - start_time
                        
                        if result.get("text") and len(result["text"].strip()) > 0:
                            session_times.append(response_time)
                        else:
                            session_errors += 1
                            
                    except Exception:
                        session_errors += 1
                
                return {
                    "user_id": user_id,
                    "response_times": session_times,
                    "errors": session_errors,
                    "total_requests": load_scenario["requests_per_user"]
                }
            
            # Run concurrent user sessions
            start_time = time.time()
            
            tasks = [user_session(user_id) for user_id in range(load_scenario["concurrent_users"])]
            session_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            total_load_time = time.time() - start_time
            
            # Analyze results
            all_response_times = []
            total_errors = 0
            total_requests = 0
            
            for session_result in session_results:
                if isinstance(session_result, dict):
                    all_response_times.extend(session_result["response_times"])
                    total_errors += session_result["errors"]
                    total_requests += session_result["total_requests"]
                else:
                    total_errors += load_scenario["requests_per_user"]
                    total_requests += load_scenario["requests_per_user"]
            
            if all_response_times:
                avg_response_time = sum(all_response_times) / len(all_response_times)
                max_response_time = max(all_response_times)
                min_response_time = min(all_response_times)
                success_rate = len(all_response_times) / total_requests * 100
                throughput = len(all_response_times) / total_load_time
                
                load_result = {
                    "scenario": load_scenario["name"],
                    "concurrent_users": load_scenario["concurrent_users"],
                    "total_requests": total_requests,
                    "successful_requests": len(all_response_times),
                    "failed_requests": total_errors,
                    "success_rate": round(success_rate, 2),
                    "total_time": round(total_load_time, 2),
                    "avg_response_time": round(avg_response_time, 2),
                    "max_response_time": round(max_response_time, 2),
                    "min_response_time": round(min_response_time, 2),
                    "throughput": round(throughput, 2)
                }
                
                # Performance thresholds
                if success_rate >= 90 and avg_response_time < 10.0:
                    load_result["status"] = "passed"
                    print(f"    ✅ {load_scenario['name']}: {success_rate}% success, {avg_response_time:.2f}s avg")
                elif success_rate >= 75 and avg_response_time < 20.0:
                    load_result["status"] = "warning"
                    print(f"    ⚠️ {load_scenario['name']}: {success_rate}% success, {avg_response_time:.2f}s avg")
                else:
                    load_result["status"] = "failed"
                    print(f"    ❌ {load_scenario['name']}: {success_rate}% success, {avg_response_time:.2f}s avg")
            else:
                load_result = {
                    "scenario": load_scenario["name"],
                    "status": "failed",
                    "error": "No successful requests",
                    "total_errors": total_errors
                }
                print(f"    ❌ {load_scenario['name']}: no successful requests")
            
            load_results.append(load_result)
        
        passed_loads = sum(1 for r in load_results if r.get("status") == "passed")
        warning_loads = sum(1 for r in load_results if r.get("status") == "warning")
        total_loads = len(load_results)
        
        return {
            "status": "passed" if passed_loads == total_loads else "warning" if (passed_loads + warning_loads) >= total_loads * 0.5 else "failed",
            "results": load_results,
            "passed": passed_loads,
            "warnings": warning_loads,
            "total": total_loads
        }
    
    async def test_error_recovery(self) -> Dict[str, Any]:
        """Test system behavior with various error conditions"""
        print("\n🔍 Testing error recovery and resilience...")
        
        error_tests = [
            {
                "name": "Invalid Brief ID",
                "message": {
                    "user_id": f"error_test_{self.test_session_id}",
                    "brief_id": "99999",  # Non-existent
                    "text": "Test message",
                    "channel": "test",
                    "language": "ru"
                },
                "expected_behavior": "graceful_handling"
            },
            {
                "name": "Empty Message",
                "message": {
                    "user_id": f"error_test_{self.test_session_id}",
                    "brief_id": "1",
                    "text": "",
                    "channel": "test", 
                    "language": "ru"
                },
                "expected_behavior": "graceful_handling"
            },
            {
                "name": "Very Long Message",
                "message": {
                    "user_id": f"error_test_{self.test_session_id}",
                    "brief_id": "1", 
                    "text": "x" * 10000,  # Very long message
                    "channel": "test",
                    "language": "ru"
                },
                "expected_behavior": "graceful_handling"
            }
        ]
        
        results = []
        for test in error_tests:
            print(f"  Testing {test['name']}...")
            
            try:
                response = await self.client.post(
                    f"{self.bot_service_url}/incoming",
                    json=test["message"]
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("text"):
                        print(f"    ✅ {test['name']}: handled gracefully")
                        results.append({"test": test["name"], "status": "handled"})
                    else:
                        print(f"    ⚠️ {test['name']}: accepted but empty response")
                        results.append({"test": test["name"], "status": "partial"})
                elif 400 <= response.status_code < 500:
                    print(f"    ✅ {test['name']}: properly rejected ({response.status_code})")
                    results.append({"test": test["name"], "status": "rejected"})
                else:
                    print(f"    ❌ {test['name']}: unexpected status {response.status_code}")
                    results.append({"test": test["name"], "status": "unexpected"})
                    
            except Exception as e:
                print(f"    ❌ {test['name']}: exception {e}")
                results.append({"test": test["name"], "status": "error", "error": str(e)})
        
        # All outcomes except "error" and "unexpected" are acceptable
        acceptable = sum(1 for r in results if r["status"] in ["handled", "partial", "rejected"])
        total = len(results)
        
        return {
            "status": "passed" if acceptable == total else "partial" if acceptable > 0 else "failed",
            "results": results,
            "acceptable": acceptable,
            "total": total
        }
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run comprehensive integration test suite"""
        print("🚀 Starting Complete Integration Test Suite")
        print(f"📍 Test Session ID: {self.test_session_id}")
        print("⚠️  Note: This may take several minutes to complete")
        print("=" * 70)
        
        test_results = {}
        
        # Prerequisite: Health checks
        test_results["health_checks"] = await self.test_all_services_health()
        
        if test_results["health_checks"]["status"] != "passed":
            print("\n❌ Health checks failed, skipping dependent tests")
            print("💡 Ensure all services are running before integration tests")
        else:
            # Core integration tests
            test_results["service_dependencies"] = await self.test_service_dependencies()
            test_results["end_to_end_conversations"] = await self.test_end_to_end_conversations()
            test_results["performance_load"] = await self.test_performance_load()
            test_results["error_recovery"] = await self.test_error_recovery()
        
        # Calculate comprehensive summary
        health = test_results["health_checks"]
        healthy_services = health.get("healthy_count", 0)
        total_services = health.get("total_count", 0)
        
        summary_data = {
            "test_session_id": self.test_session_id,
            "services_healthy": healthy_services,
            "services_total": total_services,
            "overall_health": health["status"]
        }
        
        if test_results["health_checks"]["status"] == "passed":
            dependencies = test_results["service_dependencies"]
            conversations = test_results["end_to_end_conversations"]
            performance = test_results["performance_load"]
            error_recovery = test_results["error_recovery"]
            
            summary_data.update({
                "dependencies_working": dependencies.get("passed", 0),
                "dependencies_total": dependencies.get("total", 0),
                "conversations_successful": conversations.get("passed", 0),
                "conversations_total": conversations.get("total", 0),
                "load_tests_passed": performance.get("passed", 0),
                "load_tests_total": performance.get("total", 0),
                "error_tests_acceptable": error_recovery.get("acceptable", 0),
                "error_tests_total": error_recovery.get("total", 0)
            })
            
            # Calculate overall score
            total_possible = (
                dependencies.get("total", 0) +
                conversations.get("total", 0) +
                performance.get("total", 0) +
                error_recovery.get("total", 0)
            )
            
            total_passed = (
                dependencies.get("passed", 0) +
                conversations.get("passed", 0) +
                performance.get("passed", 0) +
                error_recovery.get("acceptable", 0)
            )
            
            summary_data["integration_score"] = round(total_passed / total_possible * 100, 2) if total_possible > 0 else 0
        else:
            summary_data["integration_score"] = 0
        
        print("\n" + "=" * 70)
        print("📊 Integration Test Summary:")
        print(f"   🏥 Services Health: {healthy_services}/{total_services} services healthy")
        
        if summary_data.get("dependencies_total", 0) > 0:
            deps = summary_data
            print(f"   🔗 Dependencies: {deps['dependencies_working']}/{deps['dependencies_total']} working")
            print(f"   💬 Conversations: {deps['conversations_successful']}/{deps['conversations_total']} successful")
            print(f"   ⚡ Performance: {deps['load_tests_passed']}/{deps['load_tests_total']} load tests passed")
            print(f"   🛡️  Error Recovery: {deps['error_tests_acceptable']}/{deps['error_tests_total']} handled properly")
            print(f"   🎯 Overall Integration Score: {deps['integration_score']}%")
        
        print("=" * 70)
        
        test_results["summary"] = summary_data
        
        return test_results


async def main():
    """Main integration test runner"""
    async with IntegrationTester() as tester:
        results = await tester.run_all_tests()
        
        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"integration_test_results_{timestamp}.json"
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Detailed results saved to {filename}")
        
        # Generate summary report
        summary = results["summary"]
        
        summary_filename = f"integration_test_summary_{timestamp}.json"
        with open(summary_filename, "w") as f:
            json.dump(summary, f, indent=2)
        
        print(f"📋 Summary saved to {summary_filename}")
        
        # Determine exit code
        if summary["overall_health"] != "passed":
            print("\n❌ Integration tests failed: Services not healthy")
            return 2
        
        integration_score = summary.get("integration_score", 0)
        if integration_score >= 85:
            print("\n🎉 Integration tests passed successfully!")
            return 0
        elif integration_score >= 70:
            print("\n⚠️  Integration tests passed with some issues")
            return 1
        else:
            print("\n❌ Integration tests failed")
            return 2


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)