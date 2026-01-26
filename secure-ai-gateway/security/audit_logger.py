"""
Audit Logger
Comprehensive audit logging for AI operations, security events, and compliance.
"""
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import threading
from queue import Queue


class AuditEventType(Enum):
    """Types of audit events."""
    # Request/Response events
    REQUEST_RECEIVED = "request_received"
    RESPONSE_SENT = "response_sent"
    
    # Security events
    SECURITY_CHECK_PASSED = "security_check_passed"
    SECURITY_CHECK_FAILED = "security_check_failed"
    INJECTION_DETECTED = "injection_detected"
    PII_DETECTED = "pii_detected"
    
    # Access events
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    
    # Compliance events
    COMPLIANCE_CHECK = "compliance_check"
    POLICY_VIOLATION = "policy_violation"
    DATA_ACCESS = "data_access"
    
    # Agent events
    AGENT_TASK_STARTED = "agent_task_started"
    AGENT_TASK_COMPLETED = "agent_task_completed"
    AGENT_TOOL_CALLED = "agent_tool_called"
    AGENT_ACTION_TAKEN = "agent_action_taken"
    
    # System events
    CONFIG_CHANGE = "config_change"
    ERROR = "error"
    WARNING = "warning"


class AuditSeverity(Enum):
    """Severity levels for audit events."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Represents a single audit event."""
    event_id: str
    timestamp: str
    event_type: AuditEventType
    severity: AuditSeverity
    actor: str  # User ID, system component, or agent ID
    action: str
    resource: Optional[str]
    outcome: str  # success, failure, blocked
    details: dict = field(default_factory=dict)
    
    # Compliance-related fields
    compliance_frameworks: list[str] = field(default_factory=list)
    control_ids: list[str] = field(default_factory=list)
    
    # Context
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    # Data integrity
    checksum: Optional[str] = None
    
    def __post_init__(self):
        """Generate checksum after initialization."""
        if not self.checksum:
            self.checksum = self._generate_checksum()
    
    def _generate_checksum(self) -> str:
        """Generate SHA256 checksum for data integrity."""
        data = f"{self.event_id}{self.timestamp}{self.event_type.value}{self.actor}{self.action}{self.outcome}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "actor": self.actor,
            "action": self.action,
            "resource": self.resource,
            "outcome": self.outcome,
            "details": self.details,
            "compliance_frameworks": self.compliance_frameworks,
            "control_ids": self.control_ids,
            "session_id": self.session_id,
            "request_id": self.request_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "checksum": self.checksum
        }


class AuditLogger:
    """
    Comprehensive audit logger for AI applications.
    
    Features:
    - Structured audit logging
    - Multiple output formats (JSON, text)
    - File and console output
    - Asynchronous logging with queue
    - Compliance tagging (ISO27001, SOC2, NIST)
    - Data integrity checksums
    """
    
    def __init__(
        self,
        log_path: Path = None,
        console_output: bool = True,
        json_format: bool = True,
        async_logging: bool = True,
        retention_days: int = 365
    ):
        """
        Initialize the audit logger.
        
        Args:
            log_path: Path to log files
            console_output: Enable console output
            json_format: Use JSON format for logs
            async_logging: Use asynchronous logging
            retention_days: Log retention period
        """
        self.log_path = log_path or Path("./logs/audit")
        self.log_path.mkdir(parents=True, exist_ok=True)
        
        self.console_output = console_output
        self.json_format = json_format
        self.async_logging = async_logging
        self.retention_days = retention_days
        
        # Event counter for unique IDs
        self._event_counter = 0
        self._counter_lock = threading.Lock()
        
        # Async logging queue
        if async_logging:
            self._log_queue: Queue = Queue()
            self._logging_thread = threading.Thread(target=self._process_queue, daemon=True)
            self._logging_thread.start()
        
        # Set up Python logger
        self._logger = logging.getLogger("audit")
        self._logger.setLevel(logging.DEBUG)
        
        # File handler
        file_handler = logging.FileHandler(
            self.log_path / f"audit_{datetime.now().strftime('%Y%m%d')}.log"
        )
        file_handler.setLevel(logging.DEBUG)
        
        if json_format:
            formatter = logging.Formatter('%(message)s')
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            )
        file_handler.setFormatter(formatter)
        self._logger.addHandler(file_handler)
        
        # Console handler
        if console_output:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(formatter)
            self._logger.addHandler(console_handler)
    
    def _generate_event_id(self) -> str:
        """Generate unique event ID."""
        with self._counter_lock:
            self._event_counter += 1
            timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
            return f"EVT-{timestamp}-{self._event_counter:06d}"
    
    def log(
        self,
        event_type: AuditEventType,
        actor: str,
        action: str,
        outcome: str,
        severity: AuditSeverity = AuditSeverity.INFO,
        resource: Optional[str] = None,
        details: dict = None,
        compliance_frameworks: list[str] = None,
        control_ids: list[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditEvent:
        """
        Log an audit event.
        
        Args:
            event_type: Type of event
            actor: Who/what performed the action
            action: What action was performed
            outcome: Result of the action (success, failure, blocked)
            severity: Event severity level
            resource: Resource affected
            details: Additional event details
            compliance_frameworks: Relevant compliance frameworks
            control_ids: Related compliance control IDs
            session_id: Session identifier
            request_id: Request identifier
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            The created AuditEvent
        """
        event = AuditEvent(
            event_id=self._generate_event_id(),
            timestamp=datetime.utcnow().isoformat(),
            event_type=event_type,
            severity=severity,
            actor=actor,
            action=action,
            resource=resource,
            outcome=outcome,
            details=details or {},
            compliance_frameworks=compliance_frameworks or [],
            control_ids=control_ids or [],
            session_id=session_id,
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        if self.async_logging:
            self._log_queue.put(event)
        else:
            self._write_event(event)
        
        return event
    
    def _write_event(self, event: AuditEvent):
        """Write an event to the log."""
        if self.json_format:
            log_entry = json.dumps(event.to_dict())
        else:
            log_entry = (
                f"[{event.event_id}] {event.event_type.value} - "
                f"Actor: {event.actor} - Action: {event.action} - "
                f"Outcome: {event.outcome}"
            )
        
        level_map = {
            AuditSeverity.DEBUG: logging.DEBUG,
            AuditSeverity.INFO: logging.INFO,
            AuditSeverity.WARNING: logging.WARNING,
            AuditSeverity.ERROR: logging.ERROR,
            AuditSeverity.CRITICAL: logging.CRITICAL
        }
        
        self._logger.log(level_map[event.severity], log_entry)
    
    def _process_queue(self):
        """Process events from the async queue."""
        while True:
            event = self._log_queue.get()
            if event is None:
                break
            self._write_event(event)
            self._log_queue.task_done()
    
    # Convenience methods for common event types
    def log_request(
        self,
        actor: str,
        request_data: dict,
        session_id: Optional[str] = None
    ) -> AuditEvent:
        """Log an incoming request."""
        return self.log(
            event_type=AuditEventType.REQUEST_RECEIVED,
            actor=actor,
            action="receive_request",
            outcome="success",
            details={"request": request_data},
            session_id=session_id
        )
    
    def log_security_check(
        self,
        actor: str,
        check_type: str,
        passed: bool,
        details: dict = None,
        control_ids: list[str] = None
    ) -> AuditEvent:
        """Log a security check result."""
        return self.log(
            event_type=AuditEventType.SECURITY_CHECK_PASSED if passed else AuditEventType.SECURITY_CHECK_FAILED,
            actor=actor,
            action=f"security_check_{check_type}",
            outcome="passed" if passed else "failed",
            severity=AuditSeverity.INFO if passed else AuditSeverity.WARNING,
            details=details or {},
            compliance_frameworks=["OWASP_LLM_TOP10"],
            control_ids=control_ids or []
        )
    
    def log_compliance_check(
        self,
        actor: str,
        framework: str,
        control_id: str,
        status: str,
        details: dict = None
    ) -> AuditEvent:
        """Log a compliance check."""
        return self.log(
            event_type=AuditEventType.COMPLIANCE_CHECK,
            actor=actor,
            action=f"compliance_check_{control_id}",
            outcome=status,
            details=details or {},
            compliance_frameworks=[framework],
            control_ids=[control_id]
        )
    
    def log_agent_action(
        self,
        agent_id: str,
        action: str,
        tool: Optional[str] = None,
        result: str = "success",
        details: dict = None
    ) -> AuditEvent:
        """Log an agent action."""
        return self.log(
            event_type=AuditEventType.AGENT_ACTION_TAKEN,
            actor=agent_id,
            action=action,
            resource=tool,
            outcome=result,
            details=details or {}
        )
    
    def log_error(
        self,
        actor: str,
        error: str,
        details: dict = None
    ) -> AuditEvent:
        """Log an error event."""
        return self.log(
            event_type=AuditEventType.ERROR,
            actor=actor,
            action="error",
            outcome="failure",
            severity=AuditSeverity.ERROR,
            details={"error": error, **(details or {})}
        )
    
    def shutdown(self):
        """Shutdown the logger gracefully."""
        if self.async_logging:
            self._log_queue.put(None)
            self._logging_thread.join(timeout=5)


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def configure_audit_logger(**kwargs) -> AuditLogger:
    """Configure and return the global audit logger."""
    global _audit_logger
    _audit_logger = AuditLogger(**kwargs)
    return _audit_logger
