"""
OWASP LLM Top 10 Security Controls
Implements security controls for the OWASP Top 10 for LLM Applications.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable, Any
from datetime import datetime
import hashlib
import re


class OWASPControl(Enum):
    """OWASP LLM Top 10 Controls."""
    LLM01_PROMPT_INJECTION = "LLM01"
    LLM02_INSECURE_OUTPUT = "LLM02"
    LLM03_TRAINING_DATA_POISONING = "LLM03"
    LLM04_MODEL_DOS = "LLM04"
    LLM05_SUPPLY_CHAIN = "LLM05"
    LLM06_SENSITIVE_INFO = "LLM06"
    LLM07_INSECURE_PLUGIN = "LLM07"
    LLM08_EXCESSIVE_AGENCY = "LLM08"
    LLM09_OVERRELIANCE = "LLM09"
    LLM10_MODEL_THEFT = "LLM10"


class ControlStatus(Enum):
    """Status of a security control."""
    ENABLED = "enabled"
    DISABLED = "disabled"
    MONITORING = "monitoring"
    BLOCKING = "blocking"


@dataclass
class ControlViolation:
    """Represents a control violation."""
    control: OWASPControl
    severity: str  # low, medium, high, critical
    description: str
    evidence: str
    timestamp: str
    mitigated: bool = False
    mitigation_action: Optional[str] = None


@dataclass
class SecurityControlResult:
    """Result of security control evaluation."""
    control: OWASPControl
    passed: bool
    violations: list[ControlViolation]
    recommendations: list[str]
    metadata: dict = field(default_factory=dict)


class OWASPSecurityControls:
    """
    Implements OWASP Top 10 for LLM Applications security controls.
    
    Reference: https://owasp.org/www-project-top-10-for-large-language-model-applications/
    
    Controls:
    - LLM01: Prompt Injection
    - LLM02: Insecure Output Handling
    - LLM03: Training Data Poisoning
    - LLM04: Model Denial of Service
    - LLM05: Supply Chain Vulnerabilities
    - LLM06: Sensitive Information Disclosure
    - LLM07: Insecure Plugin Design
    - LLM08: Excessive Agency
    - LLM09: Overreliance
    - LLM10: Model Theft
    """
    
    def __init__(self):
        self.control_status: dict[OWASPControl, ControlStatus] = {
            control: ControlStatus.ENABLED for control in OWASPControl
        }
        self.violation_log: list[ControlViolation] = []
    
    # LLM01: Prompt Injection
    def check_prompt_injection(self, user_input: str, system_prompt: str = None) -> SecurityControlResult:
        """
        Check for prompt injection attempts.
        
        Mitigations:
        - Validate and sanitize all user inputs
        - Use structured prompts with clear delimiters
        - Implement privilege control for LLM access
        """
        violations = []
        recommendations = []
        
        # Check for direct injection patterns
        injection_patterns = [
            (r"(?i)ignore\s+previous\s+instructions", "Direct instruction override"),
            (r"(?i)system\s*:\s*", "System prompt injection"),
            (r"(?i)you\s+are\s+now", "Identity manipulation"),
            (r"(?i)\[INST\]|\[/INST\]|<<SYS>>|<</SYS>>", "Prompt format injection"),
        ]
        
        for pattern, description in injection_patterns:
            if re.search(pattern, user_input):
                violations.append(ControlViolation(
                    control=OWASPControl.LLM01_PROMPT_INJECTION,
                    severity="high",
                    description=description,
                    evidence=f"Pattern matched: {pattern}",
                    timestamp=datetime.utcnow().isoformat()
                ))
        
        if violations:
            recommendations.extend([
                "Implement input validation before LLM processing",
                "Use parameterized prompts instead of string concatenation",
                "Apply output-based defenses as secondary protection"
            ])
        
        return SecurityControlResult(
            control=OWASPControl.LLM01_PROMPT_INJECTION,
            passed=len(violations) == 0,
            violations=violations,
            recommendations=recommendations
        )
    
    # LLM02: Insecure Output Handling
    def check_insecure_output(self, llm_output: str) -> SecurityControlResult:
        """
        Check for insecure output handling vulnerabilities.
        
        Mitigations:
        - Validate and sanitize all LLM outputs
        - Encode output for the target context
        - Implement content security policies
        """
        violations = []
        recommendations = []
        
        # Check for potentially dangerous outputs
        dangerous_patterns = [
            (r"<script[^>]*>", "XSS payload in output"),
            (r"javascript:", "JavaScript protocol in output"),
            (r"(?i)eval\s*\(", "Code execution in output"),
            (r"(?i)document\.(cookie|location)", "DOM manipulation in output"),
        ]
        
        for pattern, description in dangerous_patterns:
            if re.search(pattern, llm_output):
                violations.append(ControlViolation(
                    control=OWASPControl.LLM02_INSECURE_OUTPUT,
                    severity="high",
                    description=description,
                    evidence=f"Dangerous pattern detected: {pattern}",
                    timestamp=datetime.utcnow().isoformat()
                ))
        
        if violations:
            recommendations.extend([
                "Sanitize LLM outputs before rendering in web contexts",
                "Use context-appropriate encoding (HTML, JS, URL)",
                "Implement Content Security Policy headers"
            ])
        
        return SecurityControlResult(
            control=OWASPControl.LLM02_INSECURE_OUTPUT,
            passed=len(violations) == 0,
            violations=violations,
            recommendations=recommendations
        )
    
    # LLM04: Model Denial of Service
    def check_model_dos(
        self, 
        input_length: int, 
        request_count: int,
        time_window_seconds: int = 60,
        max_input_length: int = 10000,
        max_requests: int = 100
    ) -> SecurityControlResult:
        """
        Check for Model DoS vulnerabilities.
        
        Mitigations:
        - Implement rate limiting
        - Set input length limits
        - Monitor resource usage
        """
        violations = []
        recommendations = []
        
        if input_length > max_input_length:
            violations.append(ControlViolation(
                control=OWASPControl.LLM04_MODEL_DOS,
                severity="medium",
                description="Input exceeds maximum length",
                evidence=f"Input length: {input_length}, Max: {max_input_length}",
                timestamp=datetime.utcnow().isoformat()
            ))
        
        if request_count > max_requests:
            violations.append(ControlViolation(
                control=OWASPControl.LLM04_MODEL_DOS,
                severity="high",
                description="Rate limit exceeded",
                evidence=f"Requests: {request_count}/{max_requests} in {time_window_seconds}s",
                timestamp=datetime.utcnow().isoformat()
            ))
        
        if violations:
            recommendations.extend([
                "Implement strict input length validation",
                "Apply rate limiting per user/session",
                "Set resource quotas for LLM operations"
            ])
        
        return SecurityControlResult(
            control=OWASPControl.LLM04_MODEL_DOS,
            passed=len(violations) == 0,
            violations=violations,
            recommendations=recommendations
        )
    
    # LLM06: Sensitive Information Disclosure
    def check_sensitive_info(self, text: str, context: str = "output") -> SecurityControlResult:
        """
        Check for sensitive information disclosure.
        
        Mitigations:
        - Implement data classification
        - Use PII detection and masking
        - Apply output filtering
        """
        violations = []
        recommendations = []
        
        # PII patterns
        sensitive_patterns = [
            (r"\b\d{3}-\d{2}-\d{4}\b", "SSN detected"),
            (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "Email detected"),
            (r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14})\b", "Credit card detected"),
            (r"(?i)(password|api[_-]?key|secret)\s*[=:]\s*\S+", "Credential detected"),
        ]
        
        for pattern, description in sensitive_patterns:
            matches = re.findall(pattern, text)
            if matches:
                violations.append(ControlViolation(
                    control=OWASPControl.LLM06_SENSITIVE_INFO,
                    severity="critical",
                    description=f"{description} in {context}",
                    evidence=f"Found {len(matches)} match(es)",
                    timestamp=datetime.utcnow().isoformat()
                ))
        
        if violations:
            recommendations.extend([
                "Implement PII detection in both inputs and outputs",
                "Use data masking/anonymization",
                "Apply least privilege access to training data"
            ])
        
        return SecurityControlResult(
            control=OWASPControl.LLM06_SENSITIVE_INFO,
            passed=len(violations) == 0,
            violations=violations,
            recommendations=recommendations
        )
    
    # LLM07: Insecure Plugin Design
    def check_plugin_security(
        self,
        plugin_name: str,
        plugin_inputs: dict,
        allowed_plugins: list[str] = None,
        input_schema: dict = None
    ) -> SecurityControlResult:
        """
        Check for insecure plugin/tool usage.
        
        Mitigations:
        - Validate plugin inputs
        - Implement plugin allowlisting
        - Apply least privilege to plugins
        """
        violations = []
        recommendations = []
        
        # Check if plugin is allowed
        if allowed_plugins and plugin_name not in allowed_plugins:
            violations.append(ControlViolation(
                control=OWASPControl.LLM07_INSECURE_PLUGIN,
                severity="high",
                description="Unauthorized plugin usage attempted",
                evidence=f"Plugin '{plugin_name}' not in allowlist",
                timestamp=datetime.utcnow().isoformat()
            ))
        
        # Validate inputs if schema provided
        if input_schema:
            required_fields = input_schema.get("required", [])
            for field in required_fields:
                if field not in plugin_inputs:
                    violations.append(ControlViolation(
                        control=OWASPControl.LLM07_INSECURE_PLUGIN,
                        severity="medium",
                        description="Missing required plugin input",
                        evidence=f"Missing field: {field}",
                        timestamp=datetime.utcnow().isoformat()
                    ))
        
        if violations:
            recommendations.extend([
                "Implement strict input validation for all plugins",
                "Use plugin allowlisting instead of blocklisting",
                "Require manual authorization for sensitive plugins"
            ])
        
        return SecurityControlResult(
            control=OWASPControl.LLM07_INSECURE_PLUGIN,
            passed=len(violations) == 0,
            violations=violations,
            recommendations=recommendations
        )
    
    # LLM08: Excessive Agency
    def check_excessive_agency(
        self,
        actions_requested: list[str],
        high_risk_actions: list[str] = None,
        requires_approval: list[str] = None,
        has_approval: bool = False
    ) -> SecurityControlResult:
        """
        Check for excessive agency risks.
        
        Mitigations:
        - Implement human-in-the-loop for sensitive actions
        - Limit autonomous capabilities
        - Require explicit approval for high-risk operations
        """
        violations = []
        recommendations = []
        
        high_risk = high_risk_actions or [
            "delete", "remove", "modify", "execute", "send_email",
            "make_payment", "update_database", "change_password"
        ]
        
        approval_needed = requires_approval or high_risk
        
        for action in actions_requested:
            if action in high_risk:
                if action in approval_needed and not has_approval:
                    violations.append(ControlViolation(
                        control=OWASPControl.LLM08_EXCESSIVE_AGENCY,
                        severity="critical",
                        description="High-risk action without approval",
                        evidence=f"Action '{action}' requires explicit approval",
                        timestamp=datetime.utcnow().isoformat()
                    ))
        
        if violations:
            recommendations.extend([
                "Implement human-in-the-loop for all high-risk actions",
                "Create clear action boundaries and approval workflows",
                "Log all actions for audit and review"
            ])
        
        return SecurityControlResult(
            control=OWASPControl.LLM08_EXCESSIVE_AGENCY,
            passed=len(violations) == 0,
            violations=violations,
            recommendations=recommendations
        )
    
    def run_all_checks(
        self,
        user_input: str = None,
        llm_output: str = None,
        actions: list[str] = None,
        plugins: list[str] = None,
        request_count: int = 0
    ) -> dict[OWASPControl, SecurityControlResult]:
        """Run all applicable security checks."""
        results = {}
        
        if user_input:
            results[OWASPControl.LLM01_PROMPT_INJECTION] = self.check_prompt_injection(user_input)
            results[OWASPControl.LLM06_SENSITIVE_INFO] = self.check_sensitive_info(user_input, "input")
            results[OWASPControl.LLM04_MODEL_DOS] = self.check_model_dos(
                len(user_input), request_count
            )
        
        if llm_output:
            results[OWASPControl.LLM02_INSECURE_OUTPUT] = self.check_insecure_output(llm_output)
            output_pii = self.check_sensitive_info(llm_output, "output")
            if OWASPControl.LLM06_SENSITIVE_INFO in results:
                results[OWASPControl.LLM06_SENSITIVE_INFO].violations.extend(output_pii.violations)
            else:
                results[OWASPControl.LLM06_SENSITIVE_INFO] = output_pii
        
        if actions:
            results[OWASPControl.LLM08_EXCESSIVE_AGENCY] = self.check_excessive_agency(actions)
        
        if plugins:
            for plugin in plugins:
                results[OWASPControl.LLM07_INSECURE_PLUGIN] = self.check_plugin_security(
                    plugin, {}, allowed_plugins=None
                )
        
        return results
    
    def get_security_summary(self, results: dict[OWASPControl, SecurityControlResult]) -> dict:
        """Generate a security summary from check results."""
        total_checks = len(results)
        passed = sum(1 for r in results.values() if r.passed)
        failed = total_checks - passed
        
        all_violations = []
        all_recommendations = set()
        
        for result in results.values():
            all_violations.extend(result.violations)
            all_recommendations.update(result.recommendations)
        
        return {
            "total_checks": total_checks,
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{(passed/total_checks)*100:.1f}%" if total_checks > 0 else "N/A",
            "violations": [
                {
                    "control": v.control.value,
                    "severity": v.severity,
                    "description": v.description
                }
                for v in all_violations
            ],
            "recommendations": list(all_recommendations),
            "timestamp": datetime.utcnow().isoformat()
        }
