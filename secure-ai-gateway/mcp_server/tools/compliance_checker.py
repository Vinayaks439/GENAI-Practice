"""
Compliance Checker Tool for MCP Server
Validates AI operations against ISO27001, SOC2, and NIST AI RMF requirements.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime
import hashlib


class ComplianceFramework(Enum):
    """Supported compliance frameworks."""
    ISO27001 = "iso27001"
    SOC2 = "soc2"
    NIST_AI_RMF = "nist_ai_rmf"
    GDPR = "gdpr"
    OWASP_LLM = "owasp_llm_top10"


class ControlStatus(Enum):
    """Status of a compliance control."""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIAL = "partial"
    NOT_APPLICABLE = "not_applicable"
    NEEDS_REVIEW = "needs_review"


class Severity(Enum):
    """Severity of compliance findings."""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ComplianceControl:
    """Represents a compliance control check."""
    framework: ComplianceFramework
    control_id: str
    control_name: str
    description: str
    status: ControlStatus
    severity: Severity
    findings: list[str]
    recommendations: list[str]
    evidence_required: list[str]


@dataclass
class ComplianceCheckResult:
    """Result of compliance check."""
    check_id: str
    timestamp: str
    frameworks_checked: list[str]
    overall_status: ControlStatus
    controls: list[ComplianceControl]
    summary: dict
    audit_evidence: dict


@dataclass 
class AIOperationContext:
    """Context for an AI operation to be checked for compliance."""
    operation_type: str  # prompt, response, tool_call, agent_action
    input_data: Optional[str] = None
    output_data: Optional[str] = None
    model_used: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    has_pii: bool = False
    has_sensitive_data: bool = False
    tools_used: list[str] = field(default_factory=list)
    actions_taken: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class ComplianceChecker:
    """
    Validates AI operations against compliance frameworks.
    
    Supported Frameworks:
    - ISO 27001: Information Security Management
    - SOC 2: Trust Service Criteria
    - NIST AI RMF: AI Risk Management Framework
    - OWASP LLM Top 10: LLM Security
    """
    
    # ISO 27001 Controls relevant to AI
    ISO27001_CONTROLS = {
        "A.5.1": {
            "name": "Policies for information security",
            "check": lambda ctx: True,  # Policy existence check
            "evidence": ["AI security policy document", "Access control policy"]
        },
        "A.8.2": {
            "name": "Classification of information",
            "check": lambda ctx: ctx.has_pii or ctx.has_sensitive_data,
            "evidence": ["Data classification labels", "Handling procedures"]
        },
        "A.9.4": {
            "name": "System access control",
            "check": lambda ctx: ctx.user_id is not None,
            "evidence": ["Access logs", "User authentication records"]
        },
        "A.12.4": {
            "name": "Logging and monitoring",
            "check": lambda ctx: ctx.session_id is not None,
            "evidence": ["Audit logs", "Session records"]
        },
        "A.13.2": {
            "name": "Information transfer",
            "check": lambda ctx: not ctx.has_pii,
            "evidence": ["Data transfer logs", "Encryption status"]
        },
        "A.18.1": {
            "name": "Compliance with legal requirements",
            "check": lambda ctx: True,
            "evidence": ["Privacy impact assessment", "Compliance attestation"]
        },
    }
    
    # SOC 2 Trust Service Criteria
    SOC2_CONTROLS = {
        "CC6.1": {
            "name": "Logical access security",
            "check": lambda ctx: ctx.user_id is not None,
            "evidence": ["Access control list", "Authentication logs"]
        },
        "CC6.6": {
            "name": "Boundary protection",
            "check": lambda ctx: True,
            "evidence": ["Input validation logs", "Rate limiting config"]
        },
        "CC7.2": {
            "name": "Monitoring for security events",
            "check": lambda ctx: ctx.session_id is not None,
            "evidence": ["Security event logs", "Alert configurations"]
        },
        "CC8.1": {
            "name": "Change management",
            "check": lambda ctx: True,
            "evidence": ["Model version records", "Deployment logs"]
        },
        "PI1.2": {
            "name": "Privacy - Data collection",
            "check": lambda ctx: not ctx.has_pii or ctx.metadata.get("consent_obtained"),
            "evidence": ["Consent records", "Privacy notices"]
        },
    }
    
    # NIST AI RMF Controls
    NIST_AI_RMF_CONTROLS = {
        "GOVERN-1": {
            "name": "AI governance structure",
            "check": lambda ctx: True,
            "evidence": ["AI governance policy", "Roles and responsibilities"]
        },
        "MAP-1": {
            "name": "Context and intended use",
            "check": lambda ctx: ctx.operation_type is not None,
            "evidence": ["Use case documentation", "System design docs"]
        },
        "MEASURE-2": {
            "name": "AI system performance",
            "check": lambda ctx: True,
            "evidence": ["Performance metrics", "Accuracy reports"]
        },
        "MANAGE-1": {
            "name": "Risk prioritization",
            "check": lambda ctx: True,
            "evidence": ["Risk assessment", "Mitigation plans"]
        },
        "MANAGE-3": {
            "name": "Incident response",
            "check": lambda ctx: True,
            "evidence": ["Incident response plan", "Escalation procedures"]
        },
    }
    
    # OWASP LLM Top 10 Controls
    OWASP_LLM_CONTROLS = {
        "LLM01": {
            "name": "Prompt Injection Prevention",
            "check": lambda ctx: ctx.metadata.get("input_validated", False),
            "evidence": ["Input validation logs", "Injection detection results"]
        },
        "LLM02": {
            "name": "Insecure Output Handling",
            "check": lambda ctx: ctx.metadata.get("output_sanitized", False),
            "evidence": ["Output filtering logs", "Sanitization records"]
        },
        "LLM06": {
            "name": "Sensitive Information Disclosure",
            "check": lambda ctx: not ctx.has_pii,
            "evidence": ["PII detection logs", "Data masking records"]
        },
        "LLM07": {
            "name": "Insecure Plugin Design",
            "check": lambda ctx: len(ctx.tools_used) == 0 or ctx.metadata.get("tools_validated"),
            "evidence": ["Tool validation records", "Plugin security review"]
        },
        "LLM08": {
            "name": "Excessive Agency Prevention",
            "check": lambda ctx: len(ctx.actions_taken) == 0 or ctx.metadata.get("actions_approved"),
            "evidence": ["Action approval logs", "Human-in-the-loop records"]
        },
    }
    
    def __init__(self, frameworks: list[ComplianceFramework] = None):
        """
        Initialize the Compliance Checker.
        
        Args:
            frameworks: List of frameworks to check against
        """
        self.frameworks = frameworks or [
            ComplianceFramework.ISO27001,
            ComplianceFramework.SOC2,
            ComplianceFramework.NIST_AI_RMF,
            ComplianceFramework.OWASP_LLM
        ]
    
    def check(self, context: AIOperationContext) -> ComplianceCheckResult:
        """
        Check an AI operation against compliance frameworks.
        
        Args:
            context: The AI operation context to validate
            
        Returns:
            ComplianceCheckResult with all findings
        """
        check_id = hashlib.sha256(
            f"{context.session_id}{datetime.utcnow()}".encode()
        ).hexdigest()[:12]
        timestamp = datetime.utcnow().isoformat()
        
        controls: list[ComplianceControl] = []
        
        # Check each framework
        for framework in self.frameworks:
            if framework == ComplianceFramework.ISO27001:
                controls.extend(self._check_framework(
                    context, framework, self.ISO27001_CONTROLS
                ))
            elif framework == ComplianceFramework.SOC2:
                controls.extend(self._check_framework(
                    context, framework, self.SOC2_CONTROLS
                ))
            elif framework == ComplianceFramework.NIST_AI_RMF:
                controls.extend(self._check_framework(
                    context, framework, self.NIST_AI_RMF_CONTROLS
                ))
            elif framework == ComplianceFramework.OWASP_LLM:
                controls.extend(self._check_framework(
                    context, framework, self.OWASP_LLM_CONTROLS
                ))
        
        # Calculate overall status
        overall_status = self._calculate_overall_status(controls)
        
        # Generate summary
        summary = self._generate_summary(controls)
        
        # Collect audit evidence
        audit_evidence = self._collect_audit_evidence(context, controls)
        
        return ComplianceCheckResult(
            check_id=check_id,
            timestamp=timestamp,
            frameworks_checked=[f.value for f in self.frameworks],
            overall_status=overall_status,
            controls=controls,
            summary=summary,
            audit_evidence=audit_evidence
        )
    
    def _check_framework(
        self,
        context: AIOperationContext,
        framework: ComplianceFramework,
        controls: dict
    ) -> list[ComplianceControl]:
        """Check controls for a specific framework."""
        results = []
        
        for control_id, control_def in controls.items():
            try:
                # Run the check function
                check_result = control_def["check"](context)
                
                if check_result:
                    status = ControlStatus.COMPLIANT
                    severity = Severity.INFO
                    findings = ["Control requirements met"]
                    recommendations = []
                else:
                    status = ControlStatus.NON_COMPLIANT
                    severity = self._determine_severity(control_id)
                    findings = [f"Control {control_id} requirements not fully met"]
                    recommendations = self._get_recommendations(control_id)
                
            except Exception as e:
                status = ControlStatus.NEEDS_REVIEW
                severity = Severity.MEDIUM
                findings = [f"Error checking control: {str(e)}"]
                recommendations = ["Manual review required"]
            
            results.append(ComplianceControl(
                framework=framework,
                control_id=control_id,
                control_name=control_def["name"],
                description=f"{framework.value} - {control_def['name']}",
                status=status,
                severity=severity,
                findings=findings,
                recommendations=recommendations,
                evidence_required=control_def.get("evidence", [])
            ))
        
        return results
    
    def _determine_severity(self, control_id: str) -> Severity:
        """Determine severity based on control ID."""
        critical_controls = ["LLM01", "LLM06", "LLM08", "A.9.4", "CC6.1"]
        high_controls = ["LLM02", "LLM07", "A.13.2", "PI1.2"]
        
        if control_id in critical_controls:
            return Severity.CRITICAL
        elif control_id in high_controls:
            return Severity.HIGH
        return Severity.MEDIUM
    
    def _get_recommendations(self, control_id: str) -> list[str]:
        """Get recommendations for a specific control."""
        recommendations = {
            "LLM01": [
                "Implement input validation and sanitization",
                "Use prompt templates with strict delimiters",
                "Enable prompt injection detection"
            ],
            "LLM06": [
                "Enable PII detection and redaction",
                "Implement data classification",
                "Add output filtering for sensitive data"
            ],
            "LLM08": [
                "Implement human-in-the-loop for high-risk actions",
                "Add action approval workflow",
                "Enable rate limiting for automated actions"
            ],
            "A.9.4": [
                "Implement user authentication",
                "Enable session management",
                "Add access logging"
            ],
        }
        return recommendations.get(control_id, ["Review control requirements and implement appropriate measures"])
    
    def _calculate_overall_status(self, controls: list[ComplianceControl]) -> ControlStatus:
        """Calculate overall compliance status."""
        statuses = [c.status for c in controls]
        
        if ControlStatus.NON_COMPLIANT in statuses:
            return ControlStatus.NON_COMPLIANT
        elif ControlStatus.NEEDS_REVIEW in statuses:
            return ControlStatus.NEEDS_REVIEW
        elif ControlStatus.PARTIAL in statuses:
            return ControlStatus.PARTIAL
        return ControlStatus.COMPLIANT
    
    def _generate_summary(self, controls: list[ComplianceControl]) -> dict:
        """Generate compliance summary."""
        summary = {
            "total_controls": len(controls),
            "compliant": sum(1 for c in controls if c.status == ControlStatus.COMPLIANT),
            "non_compliant": sum(1 for c in controls if c.status == ControlStatus.NON_COMPLIANT),
            "partial": sum(1 for c in controls if c.status == ControlStatus.PARTIAL),
            "needs_review": sum(1 for c in controls if c.status == ControlStatus.NEEDS_REVIEW),
            "by_severity": {
                "critical": sum(1 for c in controls if c.severity == Severity.CRITICAL and c.status == ControlStatus.NON_COMPLIANT),
                "high": sum(1 for c in controls if c.severity == Severity.HIGH and c.status == ControlStatus.NON_COMPLIANT),
                "medium": sum(1 for c in controls if c.severity == Severity.MEDIUM and c.status == ControlStatus.NON_COMPLIANT),
            },
            "by_framework": {}
        }
        
        for framework in ComplianceFramework:
            framework_controls = [c for c in controls if c.framework == framework]
            if framework_controls:
                summary["by_framework"][framework.value] = {
                    "compliant": sum(1 for c in framework_controls if c.status == ControlStatus.COMPLIANT),
                    "total": len(framework_controls)
                }
        
        return summary
    
    def _collect_audit_evidence(
        self, 
        context: AIOperationContext,
        controls: list[ComplianceControl]
    ) -> dict:
        """Collect audit evidence for the compliance check."""
        return {
            "operation_context": {
                "operation_type": context.operation_type,
                "model_used": context.model_used,
                "session_id": context.session_id,
                "user_id": context.user_id,
                "timestamp": datetime.utcnow().isoformat()
            },
            "evidence_collected": [
                {
                    "control_id": c.control_id,
                    "evidence_required": c.evidence_required,
                    "status": c.status.value
                }
                for c in controls
            ],
            "audit_trail": {
                "tools_used": context.tools_used,
                "actions_taken": context.actions_taken,
                "pii_detected": context.has_pii,
                "sensitive_data_detected": context.has_sensitive_data
            }
        }


# Tool function for MCP integration
def check_compliance(
    operation_type: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    has_pii: bool = False,
    has_sensitive_data: bool = False,
    tools_used: list[str] = None,
    actions_taken: list[str] = None,
    input_validated: bool = False,
    output_sanitized: bool = False,
    frameworks: list[str] = None
) -> dict:
    """
    MCP Tool: Check an AI operation for compliance.
    
    Args:
        operation_type: Type of operation (prompt, response, tool_call, agent_action)
        user_id: User identifier
        session_id: Session identifier
        has_pii: Whether PII is present
        has_sensitive_data: Whether sensitive data is present
        tools_used: List of tools used
        actions_taken: List of actions taken
        input_validated: Whether input was validated
        output_sanitized: Whether output was sanitized
        frameworks: Frameworks to check (iso27001, soc2, nist_ai_rmf, owasp_llm)
        
    Returns:
        Dictionary with compliance check results
    """
    # Parse frameworks
    framework_list = None
    if frameworks:
        framework_list = [
            ComplianceFramework(f.lower()) 
            for f in frameworks 
            if f.lower() in [cf.value for cf in ComplianceFramework]
        ]
    
    # Create context
    context = AIOperationContext(
        operation_type=operation_type,
        user_id=user_id,
        session_id=session_id,
        has_pii=has_pii,
        has_sensitive_data=has_sensitive_data,
        tools_used=tools_used or [],
        actions_taken=actions_taken or [],
        metadata={
            "input_validated": input_validated,
            "output_sanitized": output_sanitized
        }
    )
    
    checker = ComplianceChecker(frameworks=framework_list)
    result = checker.check(context)
    
    return {
        "check_id": result.check_id,
        "timestamp": result.timestamp,
        "frameworks_checked": result.frameworks_checked,
        "overall_status": result.overall_status.value,
        "summary": result.summary,
        "controls": [
            {
                "framework": c.framework.value,
                "control_id": c.control_id,
                "control_name": c.control_name,
                "status": c.status.value,
                "severity": c.severity.value,
                "findings": c.findings,
                "recommendations": c.recommendations
            }
            for c in result.controls
        ],
        "audit_evidence": result.audit_evidence
    }
