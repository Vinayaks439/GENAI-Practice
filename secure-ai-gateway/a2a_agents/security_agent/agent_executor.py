"""
A2A Security Agent - Agent Executor
Handles task execution for the A2A Security Agent.
"""
import json
import uuid
from typing import Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

# Import security tools
import sys
sys.path.insert(0, str(__file__).replace('/a2a_agents/security_agent/agent_executor.py', ''))
from mcp_server.tools import analyze_prompt, detect_pii, check_compliance


class TaskState(Enum):
    """State of a task in the A2A protocol."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class A2AMessage:
    """Message in the A2A protocol."""
    id: str
    role: str  # "user", "agent", "system"
    content: str
    timestamp: str
    metadata: dict = field(default_factory=dict)


@dataclass
class A2ATask:
    """Task in the A2A protocol."""
    id: str
    skill_id: str
    input_data: dict
    state: TaskState
    messages: list[A2AMessage] = field(default_factory=list)
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class SecurityAgentExecutor:
    """
    Executes security analysis tasks for the A2A Security Agent.
    
    This executor handles:
    - Security analysis (OWASP LLM Top 10)
    - PII detection (GDPR/CCPA compliance)
    - Compliance checking (ISO27001, SOC2, NIST)
    - Comprehensive security reports
    """
    
    def __init__(self):
        self.tasks: dict[str, A2ATask] = {}
        self.audit_log: list[dict] = []
    
    async def create_task(self, skill_id: str, input_data: dict) -> A2ATask:
        """Create a new task."""
        task_id = str(uuid.uuid4())
        
        task = A2ATask(
            id=task_id,
            skill_id=skill_id,
            input_data=input_data,
            state=TaskState.PENDING
        )
        
        self.tasks[task_id] = task
        self._log_audit("task_created", task_id, {"skill_id": skill_id})
        
        return task
    
    async def execute_task(self, task_id: str) -> A2ATask:
        """Execute a task and return the result."""
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        
        task.state = TaskState.IN_PROGRESS
        task.updated_at = datetime.utcnow().isoformat()
        
        try:
            # Add user message
            task.messages.append(A2AMessage(
                id=str(uuid.uuid4()),
                role="user",
                content=json.dumps(task.input_data),
                timestamp=datetime.utcnow().isoformat()
            ))
            
            # Execute based on skill
            if task.skill_id == "analyze_security":
                result = await self._execute_security_analysis(task.input_data)
            elif task.skill_id == "detect_pii":
                result = await self._execute_pii_detection(task.input_data)
            elif task.skill_id == "check_compliance":
                result = await self._execute_compliance_check(task.input_data)
            elif task.skill_id == "generate_report":
                result = await self._execute_security_report(task.input_data)
            else:
                raise ValueError(f"Unknown skill: {task.skill_id}")
            
            # Add agent response
            task.messages.append(A2AMessage(
                id=str(uuid.uuid4()),
                role="agent",
                content=json.dumps(result),
                timestamp=datetime.utcnow().isoformat(),
                metadata={"skill_id": task.skill_id}
            ))
            
            task.result = result
            task.state = TaskState.COMPLETED
            self._log_audit("task_completed", task_id, {"result_summary": self._summarize_result(result)})
            
        except Exception as e:
            task.state = TaskState.FAILED
            task.error = str(e)
            self._log_audit("task_failed", task_id, {"error": str(e)})
        
        task.updated_at = datetime.utcnow().isoformat()
        return task
    
    async def _execute_security_analysis(self, input_data: dict) -> dict:
        """Execute security analysis skill."""
        text = input_data.get("text", "")
        strict_mode = input_data.get("strict_mode", True)
        
        result = analyze_prompt(text, strict_mode=strict_mode)
        
        return {
            "skill": "analyze_security",
            "analysis": result,
            "summary": {
                "risk_level": result["risk_level"],
                "threats_found": len(result["threats"]),
                "is_safe": result["is_safe"]
            }
        }
    
    async def _execute_pii_detection(self, input_data: dict) -> dict:
        """Execute PII detection skill."""
        text = input_data.get("text", "")
        anonymize = input_data.get("anonymize", True)
        
        result = detect_pii(text, anonymize=anonymize)
        
        return {
            "skill": "detect_pii",
            "detection": result,
            "summary": {
                "pii_found": result["total_pii_count"],
                "requires_review": result["requires_review"],
                "sensitivity_levels": result["sensitivity_summary"]
            }
        }
    
    async def _execute_compliance_check(self, input_data: dict) -> dict:
        """Execute compliance check skill."""
        operation = input_data.get("operation", {})
        frameworks = input_data.get("frameworks", ["iso27001", "soc2", "nist_ai_rmf", "owasp_llm"])
        
        result = check_compliance(
            operation_type=operation.get("type", "prompt"),
            user_id=operation.get("user_id"),
            session_id=operation.get("session_id"),
            has_pii=operation.get("has_pii", False),
            has_sensitive_data=operation.get("has_sensitive_data", False),
            tools_used=operation.get("tools_used", []),
            actions_taken=operation.get("actions_taken", []),
            input_validated=operation.get("input_validated", False),
            output_sanitized=operation.get("output_sanitized", False),
            frameworks=frameworks
        )
        
        return {
            "skill": "check_compliance",
            "compliance": result,
            "summary": {
                "overall_status": result["overall_status"],
                "compliant_controls": result["summary"]["compliant"],
                "non_compliant_controls": result["summary"]["non_compliant"]
            }
        }
    
    async def _execute_security_report(self, input_data: dict) -> dict:
        """Execute comprehensive security report skill."""
        text = input_data.get("text", "")
        include_compliance = input_data.get("include_compliance", True)
        include_pii = input_data.get("include_pii", True)
        
        # Security analysis
        security_result = analyze_prompt(text, strict_mode=True)
        
        # PII detection
        pii_result = detect_pii(text, anonymize=True) if include_pii else None
        
        # Compliance check
        compliance_result = None
        if include_compliance:
            compliance_result = check_compliance(
                operation_type="prompt",
                has_pii=pii_result["total_pii_count"] > 0 if pii_result else False,
                has_sensitive_data=security_result["risk_level"] in ["high", "critical"],
                input_validated=True,
                output_sanitized=True
            )
        
        # Generate report
        report_id = f"SR-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
        
        return {
            "skill": "generate_report",
            "report_id": report_id,
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "overall_risk": security_result["risk_level"],
                "security_threats": len(security_result["threats"]),
                "pii_found": pii_result["total_pii_count"] if pii_result else 0,
                "compliance_status": compliance_result["overall_status"] if compliance_result else "not_checked",
                "requires_action": (
                    security_result["risk_level"] in ["high", "critical"] or
                    (pii_result and pii_result["requires_review"]) or
                    (compliance_result and compliance_result["overall_status"] != "compliant")
                )
            },
            "details": {
                "security_analysis": security_result,
                "pii_detection": pii_result,
                "compliance": compliance_result
            },
            "recommendations": self._aggregate_recommendations(
                security_result, pii_result, compliance_result
            )
        }
    
    def _aggregate_recommendations(
        self, 
        security: dict, 
        pii: Optional[dict], 
        compliance: Optional[dict]
    ) -> list[str]:
        """Aggregate recommendations from all analyses."""
        recommendations = []
        
        # Security recommendations
        recommendations.extend(security.get("recommendations", []))
        
        # PII recommendations
        if pii and pii.get("requires_review"):
            recommendations.append("Review detected PII and ensure proper handling")
            recommendations.extend(pii.get("compliance_notes", []))
        
        # Compliance recommendations
        if compliance:
            for control in compliance.get("controls", []):
                if control.get("status") == "non_compliant":
                    recommendations.extend(control.get("recommendations", []))
        
        # Deduplicate
        return list(dict.fromkeys(recommendations))[:10]
    
    def _summarize_result(self, result: dict) -> dict:
        """Create a summary of the result for audit logging."""
        return {
            "skill": result.get("skill"),
            "has_summary": "summary" in result,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _log_audit(self, event: str, task_id: str, details: dict):
        """Log an audit event."""
        self.audit_log.append({
            "event": event,
            "task_id": task_id,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details
        })
    
    def get_task(self, task_id: str) -> Optional[A2ATask]:
        """Get a task by ID."""
        return self.tasks.get(task_id)
    
    def get_audit_log(self) -> list[dict]:
        """Get the audit log."""
        return self.audit_log.copy()


# Create global executor instance
executor = SecurityAgentExecutor()


async def handle_task(skill_id: str, input_data: dict) -> dict:
    """
    Handle an incoming A2A task.
    
    This is the main entry point for A2A protocol task handling.
    """
    task = await executor.create_task(skill_id, input_data)
    task = await executor.execute_task(task.id)
    
    return {
        "task_id": task.id,
        "state": task.state.value,
        "result": task.result,
        "error": task.error,
        "messages": [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp
            }
            for msg in task.messages
        ]
    }
