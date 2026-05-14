#!/usr/bin/env python3
"""
Complete Platform Test Suite

This script runs comprehensive tests on all microservices and provides
a final assessment of the chatbot platform's readiness.

Usage:
    python test_complete_platform.py           # Full test suite
    python test_complete_platform.py --quick   # Health checks only
    python test_complete_platform.py --report  # Generate HTML report
"""

import asyncio
import httpx
import json
import os
import sys
import subprocess
from datetime import datetime
from typing import Dict, Any, List
import time

# Test configuration
SERVICES = {
    "knowledge_service": {"port": 8006, "url": "http://localhost:8006"},
    "ai_service": {"port": 8005, "url": "http://localhost:8005"},
    "auth_service": {"port": 8001, "url": "http://localhost:8001"},
    "bot_service": {"port": 8002, "url": "http://localhost:8002"},
    "api_gateway": {"port": 8000, "url": "http://localhost:8000"},
    "admin_service": {"port": 8003, "url": "http://localhost:8003"},
    "analytics_service": {"port": 8004, "url": "http://localhost:8004"},
    "web_adapter": {"port": 8007, "url": "http://localhost:8007"}
}

TEST_SCRIPTS = {
    "knowledge_service": "test_knowledge_service.py",
    "ai_service": "test_ai_service.py",
    "auth_service": "test_auth_service.py", 
    "bot_service": "test_bot_service.py",
    "api_gateway": "test_api_gateway.py",
    "admin_service": "test_admin_service.py",
    "analytics_service": "test_analytics_service.py",
    "web_adapter": "test_web_adapter.py",
    "integration": "test_integration.py"
}

class CompletePlatformTester:
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results_dir = f"complete_test_results_{self.timestamp}"
        self.ensure_results_directory()
        
    def ensure_results_directory(self):
        """Create results directory"""
        if not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir)
    
    async def check_service_health(self, service_name: str, service_config: Dict[str, Any]) -> Dict[str, Any]:
        """Check if a service is healthy"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{service_config['url']}/health")
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "service": service_name,
                        "status": "healthy",
                        "port": service_config["port"],
                        "response": data
                    }
                else:
                    return {
                        "service": service_name,
                        "status": "unhealthy",
                        "port": service_config["port"],
                        "error": f"HTTP {response.status_code}"
                    }
        except Exception as e:
            return {
                "service": service_name,
                "status": "unreachable",
                "port": service_config["port"],
                "error": str(e)
            }
    
    async def run_quick_health_checks(self) -> Dict[str, Any]:
        """Run quick health checks on all services"""
        print("🏥 Running Health Checks")
        print("=" * 50)
        
        health_results = {}
        
        for service_name, service_config in SERVICES.items():
            print(f"  Checking {service_name}...")
            result = await self.check_service_health(service_name, service_config)
            health_results[service_name] = result
            
            status_icon = "✅" if result["status"] == "healthy" else "❌"
            print(f"    {status_icon} {service_name}: {result['status']}")
        
        healthy_count = sum(1 for r in health_results.values() if r["status"] == "healthy")
        total_count = len(health_results)
        
        print(f"\n📊 Health Summary: {healthy_count}/{total_count} services healthy")
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "healthy_services": healthy_count,
            "total_services": total_count,
            "health_rate": f"{(healthy_count/total_count)*100:.1f}%",
            "services": health_results
        }
    
    def run_individual_test_script(self, script_name: str) -> Dict[str, Any]:
        """Run an individual test script"""
        try:
            print(f"  Running {script_name}...")
            
            # Use the same Python interpreter as the current process
            python_executable = sys.executable
            
            result = subprocess.run(
                [python_executable, script_name],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            return {
                "script": script_name,
                "exit_code": result.returncode,
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
        except subprocess.TimeoutExpired:
            return {
                "script": script_name,
                "exit_code": -1,
                "success": False,
                "error": "Test timeout (5 minutes)",
                "stdout": "",
                "stderr": ""
            }
        except Exception as e:
            return {
                "script": script_name,
                "exit_code": -1,
                "success": False,
                "error": str(e),
                "stdout": "",
                "stderr": ""
            }
    
    def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run all test scripts"""
        print("🧪 Running Comprehensive Tests")
        print("=" * 50)
        
        test_results = {}
        
        # Run service-specific tests
        for service, script in TEST_SCRIPTS.items():
            if os.path.exists(script):
                result = self.run_individual_test_script(script)
                test_results[service] = result
                
                status_icon = "✅" if result["success"] else "❌"
                print(f"    {status_icon} {service}: {'PASSED' if result['success'] else 'FAILED'}")
            else:
                print(f"    ⚠️  {service}: Test script not found ({script})")
                test_results[service] = {
                    "script": script,
                    "success": False,
                    "error": "Test script not found"
                }
        
        successful_tests = sum(1 for r in test_results.values() if r.get("success", False))
        total_tests = len(test_results)
        
        print(f"\n📊 Test Summary: {successful_tests}/{total_tests} tests passed")
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "successful_tests": successful_tests,
            "total_tests": total_tests,
            "success_rate": f"{(successful_tests/total_tests)*100:.1f}%",
            "tests": test_results
        }
    
    def generate_final_report(self, health_results: Dict[str, Any], test_results: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate final assessment report"""
        
        # Calculate overall scores
        health_score = (health_results["healthy_services"] / health_results["total_services"]) * 100
        
        if test_results:
            test_score = (test_results["successful_tests"] / test_results["total_tests"]) * 100
            overall_score = (health_score + test_score) / 2
        else:
            test_score = 0
            overall_score = health_score
        
        # Determine readiness level
        if overall_score >= 90:
            readiness = "🚀 PRODUCTION READY"
            readiness_color = "green"
        elif overall_score >= 75:
            readiness = "⚡ STAGING READY" 
            readiness_color = "yellow"
        elif overall_score >= 60:
            readiness = "🔧 DEVELOPMENT READY"
            readiness_color = "orange"
        else:
            readiness = "❌ NOT READY"
            readiness_color = "red"
        
        # Generate recommendations
        recommendations = []
        
        if health_results["healthy_services"] < health_results["total_services"]:
            unhealthy_services = [
                name for name, result in health_results["services"].items() 
                if result["status"] != "healthy"
            ]\n            recommendations.append(f\"Fix unhealthy services: {', '.join(unhealthy_services)}\")\n        \n        if test_results and test_results[\"successful_tests\"] < test_results[\"total_tests\"]:\n            failed_tests = [\n                name for name, result in test_results[\"tests\"].items()\n                if not result.get(\"success\", False)\n            ]\n            recommendations.append(f\"Fix failing tests: {', '.join(failed_tests)}\")\n        \n        if health_score == 100 and (not test_results or test_score >= 90):\n            recommendations.append(\"✅ Platform is ready for deployment!\")\n            recommendations.append(\"✅ Consider setting up monitoring and alerting\")\n            recommendations.append(\"✅ Configure production environment variables\")\n        \n        report = {\n            \"assessment\": {\n                \"timestamp\": datetime.utcnow().isoformat(),\n                \"overall_score\": round(overall_score, 1),\n                \"health_score\": round(health_score, 1),\n                \"test_score\": round(test_score, 1),\n                \"readiness\": readiness,\n                \"readiness_color\": readiness_color\n            },\n            \"health_results\": health_results,\n            \"test_results\": test_results,\n            \"recommendations\": recommendations,\n            \"next_steps\": [\n                \"Review failed services and tests\",\n                \"Check Docker containers are running\",\n                \"Verify network connectivity between services\", \n                \"Ensure all required environment variables are set\",\n                \"Run './scripts/setup_ollama.sh' for AI models\"\n            ]\n        }\n        \n        return report\n    \n    def print_final_assessment(self, report: Dict[str, Any]):\n        \"\"\"Print beautiful final assessment\"\"\"\n        assessment = report[\"assessment\"]\n        \n        print(\"\\n\" + \"=\" * 60)\n        print(\"🎯 FINAL PLATFORM ASSESSMENT\")\n        print(\"=\" * 60)\n        \n        print(f\"\\n{assessment['readiness']}\")\n        print(f\"Overall Score: {assessment['overall_score']}%\")\n        print(f\"  Health Score: {assessment['health_score']}%\")\n        print(f\"  Test Score: {assessment['test_score']}%\")\n        \n        if report[\"health_results\"]:\n            health = report[\"health_results\"]\n            print(f\"\\n🏥 Service Health: {health['healthy_services']}/{health['total_services']} services healthy\")\n        \n        if report[\"test_results\"]:\n            tests = report[\"test_results\"]\n            print(f\"🧪 Test Results: {tests['successful_tests']}/{tests['total_tests']} tests passed\")\n        \n        if report[\"recommendations\"]:\n            print(\"\\n💡 Recommendations:\")\n            for rec in report[\"recommendations\"]:\n                print(f\"  • {rec}\")\n        \n        print(\"\\n🔗 Quick Access URLs:\")\n        for service_name, config in SERVICES.items():\n            if service_name in [\"api_gateway\", \"admin_service\", \"web_adapter\"]:\n                if service_name == \"web_adapter\":\n                    print(f\"  • Web Chat: {config['url']}/chat\")\n                else:\n                    print(f\"  • {service_name}: {config['url']}/docs\")\n        \n        print(\"\\n\" + \"=\" * 60)\n    \n    async def run_complete_assessment(self, quick_only: bool = False) -> Dict[str, Any]:\n        \"\"\"Run complete platform assessment\"\"\"\n        print(\"🚀 Chatbot Platform Complete Assessment\")\n        print(\"=\" * 60)\n        print(f\"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\")\n        print(\"=\" * 60)\n        \n        # Always run health checks\n        health_results = await self.run_quick_health_checks()\n        \n        test_results = None\n        if not quick_only:\n            test_results = self.run_comprehensive_tests()\n        \n        # Generate final report\n        report = self.generate_final_report(health_results, test_results)\n        \n        # Save results\n        report_file = os.path.join(self.results_dir, \"platform_assessment.json\")\n        with open(report_file, 'w', encoding='utf-8') as f:\n            json.dump(report, f, indent=2, ensure_ascii=False)\n        \n        # Print assessment\n        self.print_final_assessment(report)\n        \n        print(f\"\\n💾 Full results saved to: {self.results_dir}/\")\n        \n        return report\n\ndef main():\n    \"\"\"Main execution function\"\"\"\n    import argparse\n    \n    parser = argparse.ArgumentParser(description=\"Complete Platform Test Suite\")\n    parser.add_argument(\"--quick\", action=\"store_true\", help=\"Run only health checks\")\n    parser.add_argument(\"--report\", action=\"store_true\", help=\"Generate HTML report (future feature)\")\n    \n    args = parser.parse_args()\n    \n    async def run_assessment():\n        tester = CompletePlatformTester()\n        report = await tester.run_complete_assessment(quick_only=args.quick)\n        \n        # Return appropriate exit code based on results\n        overall_score = report[\"assessment\"][\"overall_score\"]\n        if overall_score >= 75:\n            return 0  # Success\n        elif overall_score >= 50:\n            return 1  # Partial success\n        else:\n            return 2  # Major issues\n    \n    try:\n        exit_code = asyncio.run(run_assessment())\n        sys.exit(exit_code)\n    except KeyboardInterrupt:\n        print(\"\\n⚠️  Assessment interrupted by user\")\n        sys.exit(130)\n    except Exception as e:\n        print(f\"\\n❌ Assessment failed with error: {e}\")\n        sys.exit(1)\n\nif __name__ == \"__main__\":\n    main()