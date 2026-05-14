#!/usr/bin/env python3
"""
Master Test Runner for Chatbot Platform

Runs all test suites for the microservices:
- Knowledge Service
- AI Service  
- Bot Service
- API Gateway
- Integration Tests

Usage:
    python run_all_tests.py                    # Run all tests
    python run_all_tests.py --service knowledge # Run specific service tests
    python run_all_tests.py --integration      # Run only integration tests
    python run_all_tests.py --quick           # Quick health checks only
    python run_all_tests.py --report          # Generate HTML report
"""

import asyncio
import argparse
import sys
import os
import json
import subprocess
from datetime import datetime
from typing import Dict, Any, List

# Test script modules (import the test files we created)
test_scripts = {
    "knowledge": "test_knowledge_service.py",
    "ai": "test_ai_service.py", 
    "bot": "test_bot_service.py",
    "gateway": "test_api_gateway.py",
    "auth": "test_auth_service.py",
    "admin": "test_admin_service.py",
    "analytics": "test_analytics_service.py",
    "web": "test_web_adapter.py",
    "integration": "test_integration.py"
}

class MasterTestRunner:
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results_dir = f"test_results_{self.timestamp}"
        self.ensure_results_directory()
        
    def ensure_results_directory(self):
        """Create results directory"""
        if not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir)
    
    async def run_service_test(self, service_name: str) -> Dict[str, Any]:
        """Run tests for a specific service"""
        print(f"\\n🎯 Running {service_name.upper()} Service Tests")
        print("=" * 60)
        
        script_name = test_scripts.get(service_name)
        if not script_name:
            return {"status": "error", "error": f"Unknown service: {service_name}"}
        
        if not os.path.exists(script_name):
            return {"status": "error", "error": f"Test script not found: {script_name}"}
        
        try:
            # Run the test script
            result = subprocess.run([
                sys.executable, script_name
            ], capture_output=True, text=True, timeout=600)  # 10 minute timeout
            
            # Parse results if JSON file was created
            result_data = {
                "service": service_name,
                "script": script_name,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "status": "passed" if result.returncode == 0 else "failed"
            }
            
            # Try to load detailed results from JSON file
            json_files = [f for f in os.listdir(".") if f.startswith(f"{service_name}_") and f.endswith(".json")]
            if json_files:
                try:
                    with open(json_files[-1], 'r', encoding='utf-8') as f:
                        detailed_results = json.load(f)
                        result_data["detailed_results"] = detailed_results
                        
                    # Move result file to results directory
                    os.rename(json_files[-1], os.path.join(self.results_dir, json_files[-1]))
                except Exception as e:
                    result_data["json_error"] = str(e)
            
            return result_data
            
        except subprocess.TimeoutExpired:
            return {
                "service": service_name,
                "status": "timeout", 
                "error": "Test execution timed out (10 minutes)"
            }
        except Exception as e:
            return {
                "service": service_name,
                "status": "error",
                "error": str(e)
            }
    
    async def run_quick_health_checks(self) -> Dict[str, Any]:
        """Run quick health checks on all services"""
        print("\\n⚡ Running Quick Health Checks")
        print("=" * 60)
        
        import httpx
        
        services = {
            "Knowledge Service": os.getenv("KNOWLEDGE_URL", "http://localhost:8006"),
            "AI Service": os.getenv("AI_SERVICE_URL", "http://localhost:8005"),
            "Bot Service": os.getenv("BOT_SERVICE_URL", "http://localhost:8002"),
            "API Gateway": os.getenv("API_GATEWAY_URL", "http://localhost:8000"),
            "Auth Service": os.getenv("AUTH_SERVICE_URL", "http://localhost:8001")
        }
        
        results = {}
        timeout = httpx.Timeout(10.0, connect=5.0)
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            for service_name, url in services.items():
                print(f"  Checking {service_name}...")
                try:
                    response = await client.get(f"{url}/health")
                    if response.status_code == 200:
                        result = response.json()
                        status = result.get("status", "unknown")
                        print(f"    {'✅' if status in ['healthy', 'ok'] else '⚠️'} {service_name}: {status}")
                        results[service_name] = {"status": "healthy", "url": url, "response": result}
                    else:
                        print(f"    ❌ {service_name}: HTTP {response.status_code}")
                        results[service_name] = {"status": "unhealthy", "url": url, "http_code": response.status_code}
                except Exception as e:
                    print(f"    ❌ {service_name}: {e}")
                    results[service_name] = {"status": "unreachable", "url": url, "error": str(e)}
        
        healthy_count = sum(1 for r in results.values() if r["status"] == "healthy")
        total_count = len(results)
        
        print(f"\\n📊 Health Check Summary: {healthy_count}/{total_count} services healthy")
        
        return {
            "status": "passed" if healthy_count == total_count else "partial" if healthy_count > 0 else "failed",
            "results": results,
            "healthy_count": healthy_count,
            "total_count": total_count
        }
    
    async def run_all_service_tests(self) -> Dict[str, Any]:
        """Run all individual service tests"""
        services = ["knowledge", "ai", "bot", "gateway", "auth"]
        results = {}
        
        for service in services:
            result = await self.run_service_test(service)
            results[service] = result
            
            # Brief summary
            status = result.get("status", "unknown")
            if status == "passed":
                print(f"✅ {service.upper()} service tests PASSED")
            elif status == "failed":
                print(f"❌ {service.upper()} service tests FAILED")
            elif status == "timeout":
                print(f"⏰ {service.upper()} service tests TIMED OUT")
            else:
                print(f"❌ {service.upper()} service tests ERROR: {result.get('error')}")
        
        return results
    
    async def run_integration_tests(self) -> Dict[str, Any]:
        """Run integration tests"""
        print(f"\\n🔗 Running Integration Tests")
        print("=" * 60)
        
        return await self.run_service_test("integration")
    
    def generate_html_report(self, all_results: Dict[str, Any]) -> str:
        """Generate HTML test report"""
        html_template = '''
<!DOCTYPE html>
<html>
<head>
    <title>Chatbot Platform Test Results - {timestamp}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .summary {{ background: #e8f5e8; padding: 15px; margin: 20px 0; border-radius: 5px; }}
        .test-section {{ margin: 20px 0; }}
        .service-result {{ background: #f9f9f9; padding: 15px; margin: 10px 0; border-radius: 5px; }}
        .passed {{ border-left: 5px solid #28a745; }}
        .failed {{ border-left: 5px solid #dc3545; }}
        .partial {{ border-left: 5px solid #ffc107; }}
        .error {{ border-left: 5px solid #6c757d; }}
        .details {{ font-family: monospace; font-size: 12px; background: #f8f9fa; padding: 10px; margin: 10px 0; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 Chatbot Platform Test Results</h1>
        <p><strong>Timestamp:</strong> {timestamp}</p>
        <p><strong>Test Session:</strong> {test_session}</p>
    </div>
    
    <div class="summary">
        <h2>📊 Executive Summary</h2>
        {summary_content}
    </div>
    
    {sections_content}
    
    <div class="test-section">
        <h2>📁 Test Artifacts</h2>
        <p>Detailed JSON results are available in: <code>{results_dir}</code></p>
    </div>
    
    <div class="details">
        <p>Generated on {generation_time}</p>
        <p>Python version: {python_version}</p>
        <p>Working directory: {working_dir}</p>
    </div>
</body>
</html>
        '''
        
        # Generate summary content
        summary_items = []
        
        if "health_check" in all_results:
            health = all_results["health_check"]
            healthy = health.get("healthy_count", 0)
            total = health.get("total_count", 0)
            summary_items.append(f"<li>🏥 Service Health: {healthy}/{total} services healthy</li>")
        
        if "service_tests" in all_results:
            service_results = all_results["service_tests"]
            passed = sum(1 for r in service_results.values() if r.get("status") == "passed")
            total = len(service_results)
            summary_items.append(f"<li>🧪 Service Tests: {passed}/{total} test suites passed</li>")
        
        if "integration" in all_results:
            integration = all_results["integration"]
            if "detailed_results" in integration and "summary" in integration["detailed_results"]:
                score = integration["detailed_results"]["summary"].get("integration_score", 0)
                summary_items.append(f"<li>🔗 Integration Score: {score}%</li>")
        
        summary_content = "<ul>" + "".join(summary_items) + "</ul>"
        
        # Generate sections content
        sections = []
        
        if "health_check" in all_results:
            sections.append(self._generate_health_section(all_results["health_check"]))
        
        if "service_tests" in all_results:
            sections.append(self._generate_service_tests_section(all_results["service_tests"]))
        
        if "integration" in all_results:
            sections.append(self._generate_integration_section(all_results["integration"]))
        
        sections_content = "".join(sections)
        
        return html_template.format(
            timestamp=self.timestamp,
            test_session=all_results.get("test_session", "unknown"),
            summary_content=summary_content,
            sections_content=sections_content,
            results_dir=self.results_dir,
            generation_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            python_version=sys.version.split()[0],
            working_dir=os.getcwd()
        )
    
    def _generate_health_section(self, health_results: Dict[str, Any]) -> str:
        """Generate HTML for health check section"""
        status_class = {
            "healthy": "passed",
            "unhealthy": "failed", 
            "unreachable": "error"
        }
        
        rows = []
        for service, result in health_results.get("results", {}).items():
            status = result.get("status", "unknown")
            css_class = status_class.get(status, "error")
            
            rows.append(f'''
                <tr class="{css_class}">
                    <td>{service}</td>
                    <td>{status}</td>
                    <td>{result.get("url", "N/A")}</td>
                    <td>{result.get("error", result.get("http_code", "OK"))}</td>
                </tr>
            ''')
        
        return f'''
        <div class="test-section">
            <h2>🏥 Service Health Checks</h2>
            <table>
                <tr><th>Service</th><th>Status</th><th>URL</th><th>Details</th></tr>
                {"".join(rows)}
            </table>
        </div>
        '''
    
    def _generate_service_tests_section(self, service_results: Dict[str, Any]) -> str:
        """Generate HTML for service tests section"""
        sections = []
        
        for service, result in service_results.items():
            status = result.get("status", "unknown")
            css_class = {
                "passed": "passed",
                "failed": "failed", 
                "timeout": "error",
                "error": "error"
            }.get(status, "error")
            
            sections.append(f'''
            <div class="service-result {css_class}">
                <h3>{service.upper()} Service Tests</h3>
                <p><strong>Status:</strong> {status}</p>
                <p><strong>Exit Code:</strong> {result.get("exit_code", "N/A")}</p>
                {f'<p><strong>Error:</strong> {result.get("error")}</p>' if result.get("error") else ""}
            </div>
            ''')
        
        return f'''
        <div class="test-section">
            <h2>🧪 Individual Service Tests</h2>
            {"".join(sections)}
        </div>
        '''
    
    def _generate_integration_section(self, integration_result: Dict[str, Any]) -> str:
        """Generate HTML for integration tests section"""
        status = integration_result.get("status", "unknown")
        css_class = {
            "passed": "passed",
            "failed": "failed",
            "timeout": "error", 
            "error": "error"
        }.get(status, "error")
        
        content = f'''
        <div class="service-result {css_class}">
            <h3>Integration Test Results</h3>
            <p><strong>Status:</strong> {status}</p>
            <p><strong>Exit Code:</strong> {integration_result.get("exit_code", "N/A")}</p>
        '''
        
        if integration_result.get("detailed_results"):
            detailed = integration_result["detailed_results"]
            if "summary" in detailed:
                summary = detailed["summary"]
                content += f'''
                <p><strong>Integration Score:</strong> {summary.get("integration_score", "N/A")}%</p>
                <p><strong>Services Health:</strong> {summary.get("services_healthy", 0)}/{summary.get("services_total", 0)}</p>
                '''
        
        content += '</div>'
        
        return f'''
        <div class="test-section">
            <h2>🔗 Integration Tests</h2>
            {content}
        </div>
        '''
    
    def save_master_results(self, results: Dict[str, Any]) -> str:
        """Save master test results to JSON"""
        filename = os.path.join(self.results_dir, f"master_test_results_{self.timestamp}.json")
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        return filename
    
    async def run_tests(self, args: argparse.Namespace) -> Dict[str, Any]:
        """Main test execution logic"""
        results = {
            "timestamp": self.timestamp,
            "test_session": f"master_{self.timestamp}",
            "arguments": vars(args),
            "environment": {
                "python_version": sys.version,
                "working_directory": os.getcwd(),
                "platform": sys.platform
            }
        }
        
        print("🚀 Chatbot Platform Master Test Suite")
        print("=" * 70)
        print(f"📅 Test Session: {results['test_session']}")
        print(f"🔧 Python: {sys.version.split()[0]}")
        print(f"📁 Results Directory: {self.results_dir}")
        print("=" * 70)
        
        try:
            if args.quick:
                # Quick health checks only
                results["health_check"] = await self.run_quick_health_checks()
                
            elif args.service:
                # Run specific service test
                results["service_tests"] = {
                    args.service: await self.run_service_test(args.service)
                }
                
            elif args.integration:
                # Run only integration tests  
                results["integration"] = await self.run_integration_tests()
                
            else:
                # Run complete test suite
                print("\\n🔍 Phase 1: Quick Health Checks")
                results["health_check"] = await self.run_quick_health_checks()
                
                if not args.skip_services:
                    print("\\n🔍 Phase 2: Individual Service Tests")
                    results["service_tests"] = await self.run_all_service_tests()
                
                if not args.skip_integration:
                    print("\\n🔍 Phase 3: Integration Tests")  
                    results["integration"] = await self.run_integration_tests()
            
            # Save master results
            master_file = self.save_master_results(results)
            print(f"\\n💾 Master results saved to {master_file}")
            
            # Generate HTML report if requested
            if args.report:
                html_content = self.generate_html_report(results)
                html_file = os.path.join(self.results_dir, f"test_report_{self.timestamp}.html")
                
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                print(f"📊 HTML report generated: {html_file}")
            
            return results
            
        except KeyboardInterrupt:
            print("\\n⚠️ Test suite interrupted by user")
            results["status"] = "interrupted"
            return results
        except Exception as e:
            print(f"\\n❌ Test suite failed with exception: {e}")
            results["status"] = "error"
            results["error"] = str(e)
            return results

def main():
    parser = argparse.ArgumentParser(
        description="Master test runner for chatbot platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python run_all_tests.py                     # Run complete test suite
  python run_all_tests.py --quick            # Quick health checks only
  python run_all_tests.py --service knowledge # Test only knowledge service
  python run_all_tests.py --integration      # Integration tests only
  python run_all_tests.py --report           # Generate HTML report
  python run_all_tests.py --skip-integration # Skip integration tests
        '''
    )
    
    parser.add_argument("--service", 
                       choices=["knowledge", "ai", "bot", "gateway", "auth"], 
                       help="Run tests for specific service only")
    parser.add_argument("--integration", 
                       action="store_true", 
                       help="Run integration tests only")
    parser.add_argument("--quick", 
                       action="store_true",
                       help="Run quick health checks only")
    parser.add_argument("--skip-services", 
                       action="store_true",
                       help="Skip individual service tests")
    parser.add_argument("--skip-integration", 
                       action="store_true",
                       help="Skip integration tests")
    parser.add_argument("--report", 
                       action="store_true",
                       help="Generate HTML report")
    
    args = parser.parse_args()
    
    # Run tests
    async def run():
        runner = MasterTestRunner()
        results = await runner.run_tests(args)
        
        # Final summary
        print("\\n" + "=" * 70)
        print("📊 FINAL SUMMARY")
        print("=" * 70)
        
        if "health_check" in results:
            health = results["health_check"]
            print(f"🏥 Service Health: {health.get('healthy_count', 0)}/{health.get('total_count', 0)} healthy")
        
        if "service_tests" in results:
            service_results = results["service_tests"]
            passed = sum(1 for r in service_results.values() if r.get("status") == "passed")
            total = len(service_results)
            print(f"🧪 Service Tests: {passed}/{total} passed")
        
        if "integration" in results:
            integration = results["integration"]
            status = integration.get("status", "unknown")
            print(f"🔗 Integration Tests: {status}")
        
        print(f"📁 All results saved in: {runner.results_dir}")
        print("=" * 70)
        
        # Determine exit code
        if results.get("status") == "interrupted":
            return 130  # Ctrl+C
        elif results.get("status") == "error":
            return 1
        
        # Check overall success
        health_ok = results.get("health_check", {}).get("status") == "passed"
        
        if args.quick:
            return 0 if health_ok else 1
        
        service_ok = True
        if "service_tests" in results:
            service_ok = all(r.get("status") == "passed" for r in results["service_tests"].values())
        
        integration_ok = True
        if "integration" in results:
            integration_ok = results["integration"].get("status") == "passed"
        
        if health_ok and service_ok and integration_ok:
            return 0
        elif health_ok and (service_ok or integration_ok):
            return 1  # Partial success
        else:
            return 2  # Failure
    
    exit_code = asyncio.run(run())
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
