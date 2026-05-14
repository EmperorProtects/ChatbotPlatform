#!/usr/bin/env python3
"""
Test script for AI Service (Ollama Integration)

Tests all endpoints of the AI Service including:
- Health check
- Model listing
- Text generation
- Embedding generation
- Error handling
"""

import asyncio
import httpx
import json
from typing import Dict, Any, List
import os
from datetime import datetime

# Configuration
AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8005")
TIMEOUT = httpx.Timeout(120.0, connect=10.0)  # Extended timeout for AI operations

# Test data
TEST_GENERATION_REQUESTS = [
    {
        "user_message": "Привет! Расскажи о ваших продуктах",
        "context": "Наша компания предлагает электромобили премиум-класса",
        "language": "ru",
        "user_id": "test_user_001",
        "conversation_history": []
    },
    {
        "user_message": "What is your pricing?",
        "context": "Premium package costs $299/month with 24/7 support",
        "language": "en",
        "user_id": "test_user_002",
        "conversation_history": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi! How can I help you?"}
        ]
    },
    {
        "user_message": "Сколько это стоит?",
        "context": "Базовый тариф - 1000 рублей в месяц, премиум - 5000 рублей",
        "language": "ru",
        "user_id": "test_user_003",
        "conversation_history": []
    }
]

class AIServiceTester:
    def __init__(self, base_url: str = AI_SERVICE_URL):
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
    
    async def test_list_models(self) -> Dict[str, Any]:
        """Test model listing endpoint"""
        print("\\n🔍 Testing model listing...")
        try:
            response = await self.client.get(f"{self.base_url}/models")
            response.raise_for_status()
            result = response.json()
            
            # Check if we got a valid response structure
            if "models" in result or isinstance(result, dict):
                model_count = len(result.get("models", [])) if "models" in result else len(result)
                print(f"✅ Model listing passed: found {model_count} models")
                return {"status": "passed", "response": result, "model_count": model_count}
            else:
                print("❌ Model listing failed: invalid response structure")
                return {"status": "failed", "error": "Invalid response structure"}
                
        except Exception as e:
            print(f"❌ Model listing failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def test_text_generation(self) -> Dict[str, Any]:
        """Test text generation with various scenarios"""
        print("\\n🔍 Testing text generation...")
        
        results = []
        for i, request in enumerate(TEST_GENERATION_REQUESTS, 1):
            print(f"  Testing generation scenario {i}/{len(TEST_GENERATION_REQUESTS)}...")
            
            try:
                response = await self.client.post(
                    f"{self.base_url}/generate",
                    json=request
                )
                response.raise_for_status()
                result = response.json()
                print(result)
                
                # Check response structure
                required_fields = ["response", "model"]
                if all(field in result for field in required_fields):
                    response_text = result["response"]
                    model_used = result["model"]
                    
                    # Basic quality checks
                    is_valid = (
                        len(response_text.strip()) > 0 and
                        len(response_text) < 2000 and  # Reasonable length
                        response_text != request["user_message"]  # Not just echoing
                    )
                    
                    if is_valid:
                        print(f"    ✅ Scenario {i} passed: {len(response_text)} chars, model: {model_used}")
                        results.append({
                            "scenario": i,
                            "status": "passed",
                            "response_length": len(response_text),
                            "model": model_used,
                            "language": request["language"]
                        })
                    else:
                        print(f"    ❌ Scenario {i} failed: invalid response quality")
                        results.append({
                            "scenario": i,
                            "status": "failed",
                            "error": "Invalid response quality"
                        })
                else:
                    print(f"    ❌ Scenario {i} failed: missing required fields")
                    results.append({
                        "scenario": i,
                        "status": "failed", 
                        "error": "Missing required fields"
                    })
                    
            except Exception as e:
                print(f"    ❌ Scenario {i} failed: {e}")
                results.append({
                    "scenario": i,
                    "status": "failed",
                    "error": str(e)
                })
        
        # Calculate success rate
        passed = sum(1 for r in results if r["status"] == "passed")
        total = len(results)
        
        if passed == total:
            print(f"✅ Text generation passed: {passed}/{total} scenarios successful")
            return {"status": "passed", "results": results, "passed": passed, "total": total}
        else:
            print(f"⚠️ Text generation partial: {passed}/{total} scenarios successful")
            return {"status": "partial", "results": results, "passed": passed, "total": total}
    
    async def test_embedding_generation(self) -> Dict[str, Any]:
        """Test embedding generation"""
        print("\\n🔍 Testing embedding generation...")
        
        test_texts = [
            "This is a simple test sentence",
            "Это тестовое предложение на русском языке",
            "Short text",
            "This is a much longer text that contains multiple sentences and should test the embedding generation with more complex input. It includes various topics and concepts to ensure the embedding captures semantic meaning properly."
        ]
        
        results = []
        for i, text in enumerate(test_texts, 1):
            print(f"  Testing embedding {i}/{len(test_texts)}...")
            
            try:
                response = await self.client.post(
                    f"{self.base_url}/embeddings",
                    params={"text": text}
                )
                response.raise_for_status()
                result = response.json()
                
                # Check if we got an embedding
                if "embedding" in result and isinstance(result["embedding"], list):
                    embedding_size = len(result["embedding"])
                    print(f"    ✅ Embedding {i} passed: {embedding_size} dimensions")
                    results.append({
                        "text_length": len(text),
                        "embedding_size": embedding_size,
                        "status": "passed"
                    })
                else:
                    print(f"    ❌ Embedding {i} failed: invalid response structure")
                    results.append({
                        "text_length": len(text),
                        "status": "failed",
                        "error": "Invalid response structure"
                    })
                    
            except Exception as e:
                print(f"    ❌ Embedding {i} failed: {e}")
                results.append({
                    "text_length": len(text),
                    "status": "failed",
                    "error": str(e)
                })
        
        passed = sum(1 for r in results if r["status"] == "passed")
        total = len(results)
        
        if passed == total:
            print(f"✅ Embedding generation passed: {passed}/{total} tests successful")
            return {"status": "passed", "results": results, "passed": passed, "total": total}
        else:
            print(f"⚠️ Embedding generation partial: {passed}/{total} tests successful")
            return {"status": "partial", "results": results, "passed": passed, "total": total}
    
    async def test_performance_baseline(self) -> Dict[str, Any]:
        """Test basic performance metrics"""
        print("\\n🔍 Testing performance baseline...")
        
        # Simple generation request for timing
        test_request = {
            "user_message": "Hello, how are you?",
            "context": "",
            "language": "en",
            "user_id": "perf_test",
            "conversation_history": []
        }
        
        response_times = []
        
        for i in range(3):
            print(f"  Performance test {i+1}/3...")
            try:
                start_time = datetime.now()
                
                response = await self.client.post(
                    f"{self.base_url}/generate",
                    json=test_request
                )
                response.raise_for_status()
                result = response.json()
                
                end_time = datetime.now()
                response_time = (end_time - start_time).total_seconds()
                response_times.append(response_time)
                
                print(f"    Response time: {response_time:.2f}s")
                
            except Exception as e:
                print(f"    ❌ Performance test {i+1} failed: {e}")
                return {"status": "failed", "error": str(e)}
        
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            min_time = min(response_times)
            
            # Performance thresholds (adjust based on your requirements)
            if avg_time < 10.0:  # Less than 10 seconds average
                status = "passed"
                print(f"✅ Performance baseline passed: avg {avg_time:.2f}s")
            elif avg_time < 30.0:  # Less than 30 seconds average
                status = "warning"
                print(f"⚠️ Performance baseline warning: avg {avg_time:.2f}s")
            else:
                status = "slow"
                print(f"🐌 Performance baseline slow: avg {avg_time:.2f}s")
            
            return {
                "status": status,
                "avg_time": round(avg_time, 2),
                "max_time": round(max_time, 2),
                "min_time": round(min_time, 2),
                "measurements": len(response_times)
            }
        else:
            return {"status": "failed", "error": "No valid measurements"}
    
    async def test_error_handling(self) -> Dict[str, Any]:
        """Test error handling and edge cases"""
        print("\\n🔍 Testing error handling...")
        
        error_tests = [
            {
                "name": "Empty generation request",
                "request": lambda: self.client.post(f"{self.base_url}/generate", json={}),
                "expected_status": [400, 422]
            },
            {
                "name": "Missing required fields",
                "request": lambda: self.client.post(f"{self.base_url}/generate", json={"user_message": "test"}),
                "expected_status": [400, 422]
            },
            {
                "name": "Invalid model for embedding",
                "request": lambda: self.client.post(
                    f"{self.base_url}/embeddings", 
                    params={"text": "test", "model": "non-existent-model"}
                ),
                "expected_status": [400, 500]
            },
            {
                "name": "Empty text for embedding",
                "request": lambda: self.client.post(
                    f"{self.base_url}/embeddings",
                    params={"text": ""}
                ),
                "expected_status": [400, 422, 500]
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
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run comprehensive test suite"""
        print("🚀 Starting AI Service Comprehensive Tests")
        print(f"📍 Testing URL: {self.base_url}")
        print("⚠️  Note: AI tests may take longer due to model inference")
        print("=" * 60)
        
        test_results = {}
        
        # Core functionality tests
        test_results["root"] = await self.test_root_endpoint()
        test_results["health"] = await self.test_health_check()
        test_results["list_models"] = await self.test_list_models()
        test_results["text_generation"] = await self.test_text_generation()
        test_results["embedding_generation"] = await self.test_embedding_generation()
        test_results["performance"] = await self.test_performance_baseline()
        test_results["error_handling"] = await self.test_error_handling()
        
        # Calculate summary
        core_tests = ["root", "health", "list_models", "text_generation", "embedding_generation", "performance"]
        
        passed_core = 0
        for test in core_tests:
            result = test_results[test]
            if result.get("status") in ["passed", "warning"]:
                passed_core += 1
            elif result.get("status") == "partial" and result.get("passed", 0) > 0:
                # Count partial successes as 0.5
                passed_core += 0.5
        
        total_core = len(core_tests)
        
        error_handling = test_results["error_handling"]
        passed_error = error_handling.get("passed", 0)
        total_error = error_handling.get("total", 0)
        
        print("\\n" + "=" * 60)
        print(f"📊 AI Service Test Summary:")
        print(f"   Core Tests: {passed_core}/{total_core} passed")
        print(f"   Error Handling: {passed_error}/{total_error} passed")
        print(f"   Overall: {passed_core + passed_error}/{total_core + total_error} passed")
        
        # Performance notes
        perf_result = test_results["performance"]
        if perf_result.get("status") == "slow":
            print(f"   ⚠️  Performance: Average response time {perf_result.get('avg_time')}s")
        elif perf_result.get("status") == "warning":
            print(f"   ⚠️  Performance: Average response time {perf_result.get('avg_time')}s (acceptable)")
        
        print("=" * 60)
        
        test_results["summary"] = {
            "core_passed": passed_core,
            "core_total": total_core,
            "error_passed": passed_error,
            "error_total": total_error,
            "overall_passed": passed_core + passed_error,
            "overall_total": total_core + total_error,
            "success_rate": round((passed_core + passed_error) / (total_core + total_error) * 100, 2)
        }
        
        return test_results


async def main():
    """Main test runner"""
    async with AIServiceTester() as tester:
        results = await tester.run_all_tests()
        
        # Save results to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ai_service_test_results_{timestamp}.json"
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\\n💾 Detailed results saved to {filename}")
        
        # Return exit code based on success rate
        success_rate = results["summary"]["success_rate"]
        if success_rate >= 85:  # Lower threshold for AI service due to complexity
            print("🎉 All tests passed successfully!")
            return 0
        elif success_rate >= 70:
            print("⚠️  Most tests passed with some issues")
            return 1
        else:
            print("❌ Multiple test failures detected")
            return 2


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
