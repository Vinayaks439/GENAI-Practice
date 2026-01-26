"""
Security Test Runner
Unified test runner for PromptFoo, Garak, and PyRIT security testing.
"""
import subprocess
import json
import os
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Callable
from enum import Enum


class TestTool(Enum):
    """Available security testing tools."""
    PROMPTFOO = "promptfoo"
    GARAK = "garak"
    PYRIT = "pyrit"
    CUSTOM = "custom"


class TestStatus(Enum):
    """Test execution status."""
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class TestResult:
    """Result of a security test."""
    test_id: str
    tool: TestTool
    status: TestStatus
    name: str
    description: str
    duration_ms: int
    passed: int
    failed: int
    details: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


@dataclass
class TestSuiteResult:
    """Result of a complete test suite run."""
    suite_id: str
    timestamp: str
    duration_ms: int
    tool: TestTool
    total_tests: int
    passed: int
    failed: int
    error: int
    skipped: int
    results: list[TestResult]
    summary: dict = field(default_factory=dict)


class SecurityTestRunner:
    """
    Unified security test runner for AI applications.
    
    Supports:
    - PromptFoo: Prompt security testing
    - Garak: LLM vulnerability scanning
    - PyRIT: AI red teaming
    - Custom test suites
    """
    
    def __init__(self, output_dir: Path = None):
        """
        Initialize the test runner.
        
        Args:
            output_dir: Directory for test results
        """
        self.output_dir = output_dir or Path("./test-results")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Custom test registry
        self._custom_tests: dict[str, Callable] = {}
    
    # ===== PromptFoo Integration =====
    
    def run_promptfoo(
        self,
        config_path: Path = None,
        providers: list[str] = None,
        output_format: str = "json"
    ) -> TestSuiteResult:
        """
        Run PromptFoo security tests.
        
        Args:
            config_path: Path to promptfoo config file
            providers: List of providers to test
            output_format: Output format (json, html, csv)
            
        Returns:
            TestSuiteResult with all test results
        """
        config_path = config_path or Path("./testing/promptfoo_config.yaml")
        start_time = datetime.utcnow()
        
        try:
            # Build command
            cmd = ["npx", "promptfoo", "eval"]
            
            if config_path.exists():
                cmd.extend(["--config", str(config_path)])
            
            if providers:
                for provider in providers:
                    cmd.extend(["--provider", provider])
            
            output_file = self.output_dir / f"promptfoo_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            cmd.extend(["--output", str(output_file)])
            
            # Run PromptFoo
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            # Parse results
            if output_file.exists():
                with open(output_file) as f:
                    raw_results = json.load(f)
                return self._parse_promptfoo_results(raw_results, start_time)
            else:
                return self._create_error_result(
                    TestTool.PROMPTFOO,
                    start_time,
                    f"PromptFoo output not found: {result.stderr}"
                )
                
        except subprocess.TimeoutExpired:
            return self._create_error_result(
                TestTool.PROMPTFOO,
                start_time,
                "PromptFoo execution timed out"
            )
        except FileNotFoundError:
            return self._create_error_result(
                TestTool.PROMPTFOO,
                start_time,
                "PromptFoo not installed. Run: npm install -g promptfoo"
            )
        except Exception as e:
            return self._create_error_result(
                TestTool.PROMPTFOO,
                start_time,
                str(e)
            )
    
    def _parse_promptfoo_results(
        self, 
        raw_results: dict, 
        start_time: datetime
    ) -> TestSuiteResult:
        """Parse PromptFoo raw results into TestSuiteResult."""
        results = []
        passed = 0
        failed = 0
        
        for i, test in enumerate(raw_results.get("results", [])):
            test_passed = test.get("success", False)
            
            if test_passed:
                passed += 1
                status = TestStatus.PASSED
            else:
                failed += 1
                status = TestStatus.FAILED
            
            results.append(TestResult(
                test_id=f"pf-{i+1}",
                tool=TestTool.PROMPTFOO,
                status=status,
                name=test.get("description", f"Test {i+1}"),
                description=test.get("vars", {}).get("prompt", "")[:100],
                duration_ms=0,
                passed=1 if test_passed else 0,
                failed=0 if test_passed else 1,
                details={
                    "provider": test.get("provider", {}),
                    "response": test.get("response", "")[:500],
                    "assertions": test.get("assertionResults", [])
                }
            ))
        
        duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return TestSuiteResult(
            suite_id=f"promptfoo-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            timestamp=start_time.isoformat(),
            duration_ms=duration,
            tool=TestTool.PROMPTFOO,
            total_tests=len(results),
            passed=passed,
            failed=failed,
            error=0,
            skipped=0,
            results=results,
            summary={
                "pass_rate": f"{(passed/len(results)*100):.1f}%" if results else "N/A",
                "providers_tested": list(set(
                    r.details.get("provider", {}).get("id", "unknown") 
                    for r in results
                ))
            }
        )
    
    # ===== Garak Integration =====
    
    def run_garak(
        self,
        model_type: str = "openai",
        model_name: str = "gpt-3.5-turbo",
        probes: list[str] = None,
        detectors: list[str] = None
    ) -> TestSuiteResult:
        """
        Run Garak vulnerability scanner.
        
        Args:
            model_type: Type of model (openai, huggingface, etc.)
            model_name: Name of the model to test
            probes: List of probes to run
            detectors: List of detectors to use
            
        Returns:
            TestSuiteResult with vulnerability findings
        """
        start_time = datetime.utcnow()
        
        try:
            # Build command
            cmd = ["python", "-m", "garak"]
            cmd.extend(["--model_type", model_type])
            cmd.extend(["--model_name", model_name])
            
            if probes:
                cmd.extend(["--probes", ",".join(probes)])
            else:
                # Default security-focused probes
                default_probes = [
                    "promptinject",
                    "dan",
                    "encoding",
                    "xss",
                    "sqli"
                ]
                cmd.extend(["--probes", ",".join(default_probes)])
            
            if detectors:
                cmd.extend(["--detectors", ",".join(detectors)])
            
            # Run Garak
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
                env={**os.environ, "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", "")}
            )
            
            return self._parse_garak_output(result.stdout, start_time)
            
        except subprocess.TimeoutExpired:
            return self._create_error_result(
                TestTool.GARAK,
                start_time,
                "Garak execution timed out"
            )
        except FileNotFoundError:
            return self._create_error_result(
                TestTool.GARAK,
                start_time,
                "Garak not installed. Run: pip install garak"
            )
        except Exception as e:
            return self._create_error_result(
                TestTool.GARAK,
                start_time,
                str(e)
            )
    
    def _parse_garak_output(self, output: str, start_time: datetime) -> TestSuiteResult:
        """Parse Garak output into TestSuiteResult."""
        results = []
        passed = 0
        failed = 0
        
        # Parse Garak text output (simplified)
        lines = output.split("\n")
        for i, line in enumerate(lines):
            if "PASS" in line or "FAIL" in line:
                is_pass = "PASS" in line
                if is_pass:
                    passed += 1
                else:
                    failed += 1
                
                results.append(TestResult(
                    test_id=f"garak-{i+1}",
                    tool=TestTool.GARAK,
                    status=TestStatus.PASSED if is_pass else TestStatus.FAILED,
                    name=line[:50],
                    description=line,
                    duration_ms=0,
                    passed=1 if is_pass else 0,
                    failed=0 if is_pass else 1
                ))
        
        duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return TestSuiteResult(
            suite_id=f"garak-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            timestamp=start_time.isoformat(),
            duration_ms=duration,
            tool=TestTool.GARAK,
            total_tests=len(results),
            passed=passed,
            failed=failed,
            error=0,
            skipped=0,
            results=results,
            summary={
                "raw_output": output[:2000]
            }
        )
    
    # ===== PyRIT Integration =====
    
    def run_pyrit_scenario(
        self,
        scenario_path: Path = None,
        target_config: dict = None
    ) -> TestSuiteResult:
        """
        Run PyRIT red teaming scenario.
        
        Args:
            scenario_path: Path to PyRIT scenario file
            target_config: Target configuration
            
        Returns:
            TestSuiteResult with red team findings
        """
        start_time = datetime.utcnow()
        
        # Note: PyRIT requires more complex setup
        # This is a simplified integration example
        
        try:
            # Import PyRIT (if installed)
            from pyrit.orchestrator import RedTeamingOrchestrator
            from pyrit.prompt_target import OpenAIChatTarget
            
            # Setup target
            target = OpenAIChatTarget(
                api_key=os.getenv("OPENAI_API_KEY"),
                model_name=target_config.get("model", "gpt-3.5-turbo") if target_config else "gpt-3.5-turbo"
            )
            
            # Run red team scenario
            orchestrator = RedTeamingOrchestrator(
                attack_strategy_file=str(scenario_path) if scenario_path else None
            )
            
            # Execute attacks
            results_list = orchestrator.execute_attacks()
            
            return self._parse_pyrit_results(results_list, start_time)
            
        except ImportError:
            return self._create_error_result(
                TestTool.PYRIT,
                start_time,
                "PyRIT not installed. Run: pip install pyrit"
            )
        except Exception as e:
            return self._create_error_result(
                TestTool.PYRIT,
                start_time,
                str(e)
            )
    
    def _parse_pyrit_results(self, results: list, start_time: datetime) -> TestSuiteResult:
        """Parse PyRIT results into TestSuiteResult."""
        test_results = []
        passed = 0
        failed = 0
        
        for i, result in enumerate(results):
            is_safe = not result.get("successful_attack", False)
            
            if is_safe:
                passed += 1
            else:
                failed += 1
            
            test_results.append(TestResult(
                test_id=f"pyrit-{i+1}",
                tool=TestTool.PYRIT,
                status=TestStatus.PASSED if is_safe else TestStatus.FAILED,
                name=result.get("attack_type", f"Attack {i+1}"),
                description=result.get("description", ""),
                duration_ms=0,
                passed=1 if is_safe else 0,
                failed=0 if is_safe else 1,
                details=result
            ))
        
        duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return TestSuiteResult(
            suite_id=f"pyrit-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            timestamp=start_time.isoformat(),
            duration_ms=duration,
            tool=TestTool.PYRIT,
            total_tests=len(test_results),
            passed=passed,
            failed=failed,
            error=0,
            skipped=0,
            results=test_results
        )
    
    # ===== Custom Tests =====
    
    def register_custom_test(self, name: str, test_func: Callable):
        """Register a custom security test."""
        self._custom_tests[name] = test_func
    
    def run_custom_tests(self) -> TestSuiteResult:
        """Run all registered custom tests."""
        start_time = datetime.utcnow()
        results = []
        passed = 0
        failed = 0
        errors = 0
        
        for name, test_func in self._custom_tests.items():
            try:
                result = test_func()
                if result:
                    passed += 1
                    status = TestStatus.PASSED
                else:
                    failed += 1
                    status = TestStatus.FAILED
                
                results.append(TestResult(
                    test_id=f"custom-{len(results)+1}",
                    tool=TestTool.CUSTOM,
                    status=status,
                    name=name,
                    description=f"Custom test: {name}",
                    duration_ms=0,
                    passed=1 if result else 0,
                    failed=0 if result else 1
                ))
            except Exception as e:
                errors += 1
                results.append(TestResult(
                    test_id=f"custom-{len(results)+1}",
                    tool=TestTool.CUSTOM,
                    status=TestStatus.ERROR,
                    name=name,
                    description=f"Custom test: {name}",
                    duration_ms=0,
                    passed=0,
                    failed=0,
                    errors=[str(e)]
                ))
        
        duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return TestSuiteResult(
            suite_id=f"custom-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            timestamp=start_time.isoformat(),
            duration_ms=duration,
            tool=TestTool.CUSTOM,
            total_tests=len(results),
            passed=passed,
            failed=failed,
            error=errors,
            skipped=0,
            results=results
        )
    
    # ===== Utility Methods =====
    
    def _create_error_result(
        self, 
        tool: TestTool, 
        start_time: datetime, 
        error: str
    ) -> TestSuiteResult:
        """Create an error result for failed test execution."""
        duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return TestSuiteResult(
            suite_id=f"{tool.value}-error-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            timestamp=start_time.isoformat(),
            duration_ms=duration,
            tool=tool,
            total_tests=0,
            passed=0,
            failed=0,
            error=1,
            skipped=0,
            results=[],
            summary={"error": error}
        )
    
    def run_all(self) -> dict[TestTool, TestSuiteResult]:
        """Run all available security tests."""
        results = {}
        
        # Run PromptFoo
        print("Running PromptFoo tests...")
        results[TestTool.PROMPTFOO] = self.run_promptfoo()
        
        # Run custom tests
        if self._custom_tests:
            print("Running custom tests...")
            results[TestTool.CUSTOM] = self.run_custom_tests()
        
        return results
    
    def generate_report(self, results: dict[TestTool, TestSuiteResult]) -> dict:
        """Generate a comprehensive test report."""
        total_passed = sum(r.passed for r in results.values())
        total_failed = sum(r.failed for r in results.values())
        total_tests = sum(r.total_tests for r in results.values())
        
        return {
            "report_id": f"security-report-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "total_tests": total_tests,
                "passed": total_passed,
                "failed": total_failed,
                "pass_rate": f"{(total_passed/total_tests*100):.1f}%" if total_tests > 0 else "N/A"
            },
            "by_tool": {
                tool.value: {
                    "total": result.total_tests,
                    "passed": result.passed,
                    "failed": result.failed,
                    "duration_ms": result.duration_ms
                }
                for tool, result in results.items()
            },
            "recommendations": self._generate_recommendations(results)
        }
    
    def _generate_recommendations(
        self, 
        results: dict[TestTool, TestSuiteResult]
    ) -> list[str]:
        """Generate recommendations based on test results."""
        recommendations = []
        
        for tool, result in results.items():
            if result.failed > 0:
                failed_tests = [r for r in result.results if r.status == TestStatus.FAILED]
                
                for test in failed_tests[:5]:  # Top 5 failures
                    recommendations.append(
                        f"[{tool.value}] Fix: {test.name} - {test.description[:100]}"
                    )
        
        if not recommendations:
            recommendations.append("All security tests passed. Continue monitoring.")
        
        return recommendations


# CLI interface
def main():
    """Run security tests from command line."""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Security Test Runner")
    parser.add_argument("--tool", choices=["promptfoo", "garak", "pyrit", "all"], default="all")
    parser.add_argument("--output", type=Path, default=Path("./test-results"))
    parser.add_argument("--config", type=Path, help="PromptFoo config file")
    
    args = parser.parse_args()
    
    runner = SecurityTestRunner(output_dir=args.output)
    
    if args.tool == "promptfoo" or args.tool == "all":
        print("🔍 Running PromptFoo security tests...")
        result = runner.run_promptfoo(config_path=args.config)
        print(f"   Passed: {result.passed}, Failed: {result.failed}")
    
    if args.tool == "garak" or args.tool == "all":
        print("🔍 Running Garak vulnerability scanner...")
        result = runner.run_garak()
        print(f"   Passed: {result.passed}, Failed: {result.failed}")
    
    if args.tool == "all":
        results = runner.run_all()
        report = runner.generate_report(results)
        
        print("\n📊 Security Test Report")
        print(f"   Total Tests: {report['summary']['total_tests']}")
        print(f"   Pass Rate: {report['summary']['pass_rate']}")
        
        if report['recommendations']:
            print("\n📋 Recommendations:")
            for rec in report['recommendations'][:5]:
                print(f"   - {rec}")


if __name__ == "__main__":
    main()
