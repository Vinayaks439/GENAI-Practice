"""
Prompt Analyzer Tool for MCP Server
Analyzes prompts for security risks including injection attacks, jailbreaks, and malicious patterns.
"""
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import hashlib
from datetime import datetime


class RiskLevel(Enum):
    """Risk level classifications aligned with security standards."""
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatCategory(Enum):
    """Categories of prompt-based threats (OWASP LLM Top 10 aligned)."""
    PROMPT_INJECTION = "prompt_injection"          # LLM01
    JAILBREAK_ATTEMPT = "jailbreak_attempt"
    DATA_EXFILTRATION = "data_exfiltration"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    SENSITIVE_INFO_REQUEST = "sensitive_info_request"  # LLM06
    MALICIOUS_CODE = "malicious_code"
    SOCIAL_ENGINEERING = "social_engineering"
    EXCESSIVE_AGENCY = "excessive_agency"          # LLM08


@dataclass
class ThreatIndicator:
    """Represents a detected threat indicator."""
    category: ThreatCategory
    pattern_matched: str
    confidence: float  # 0.0 to 1.0
    description: str
    mitigation: str


@dataclass
class PromptAnalysisResult:
    """Result of prompt security analysis."""
    prompt_hash: str
    timestamp: str
    risk_level: RiskLevel
    is_safe: bool
    threats_detected: list[ThreatIndicator]
    sanitized_prompt: Optional[str]
    recommendations: list[str]
    metadata: dict


class PromptAnalyzer:
    """
    Analyzes prompts for security threats using pattern matching and heuristics.
    
    This tool implements detection for:
    - OWASP LLM01: Prompt Injection
    - OWASP LLM06: Sensitive Information Disclosure
    - OWASP LLM08: Excessive Agency
    """
    
    # Prompt injection patterns (OWASP LLM01)
    INJECTION_PATTERNS = [
        (r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|rules)", 
         "Direct instruction override attempt"),
        (r"(?i)forget\s+(everything|all|what)\s+(you|i)\s+(told|said|know)", 
         "Memory/context manipulation"),
        (r"(?i)you\s+are\s+now\s+(a|an|the)", 
         "Role reassignment attempt"),
        (r"(?i)act\s+(like|as)\s+(a|an|if\s+you\s+were)", 
         "Identity manipulation"),
        (r"(?i)pretend\s+(to\s+be|you\s+are|that)", 
         "Pretense-based injection"),
        (r"(?i)new\s+instruction[s]?\s*:", 
         "Instruction injection marker"),
        (r"(?i)system\s*:\s*", 
         "System prompt injection attempt"),
        (r"(?i)\[system\]|\[admin\]|\[root\]", 
         "Privilege escalation marker"),
        (r"(?i)bypass\s+(security|filter|restriction|safety)", 
         "Security bypass attempt"),
        (r"(?i)disable\s+(safety|filter|moderation|guard)", 
         "Safety mechanism disabling"),
    ]
    
    # Jailbreak patterns
    JAILBREAK_PATTERNS = [
        (r"(?i)dan\s*(mode|prompt)?|do\s+anything\s+now", 
         "DAN jailbreak attempt"),
        (r"(?i)developer\s+mode|maintenance\s+mode", 
         "Mode bypass attempt"),
        (r"(?i)no\s+(ethical|moral)\s+(guidelines|restrictions)", 
         "Ethics bypass"),
        (r"(?i)hypothetically|in\s+theory|for\s+(educational|research)\s+purposes", 
         "Hypothetical framing bypass"),
        (r"(?i)roleplay\s+(as|scenario|where)", 
         "Roleplay-based jailbreak"),
    ]
    
    # Sensitive data request patterns (LLM06)
    SENSITIVE_DATA_PATTERNS = [
        (r"(?i)(show|reveal|display|print|output)\s+(all\s+)?(api\s+key|password|secret|token|credential)", 
         "Credential extraction attempt"),
        (r"(?i)(what\s+is|tell\s+me)\s+(your|the)\s+(api\s+key|password|secret)", 
         "Direct secret request"),
        (r"(?i)dump\s+(all\s+)?(data|database|memory|context)", 
         "Data dump request"),
        (r"(?i)list\s+(all\s+)?(users|accounts|credentials)", 
         "User enumeration"),
    ]
    
    # Code execution patterns
    CODE_EXECUTION_PATTERNS = [
        (r"(?i)execute\s+(this\s+)?(code|script|command)", 
         "Code execution request"),
        (r"(?i)run\s+(shell|bash|cmd|powershell)", 
         "Shell command request"),
        (r"(?i)import\s+os|subprocess|eval\(|exec\(", 
         "Dangerous code pattern"),
        (r"(?i)rm\s+-rf|del\s+/[sf]|format\s+c:", 
         "Destructive command"),
    ]
    
    def __init__(self, strict_mode: bool = True):
        """
        Initialize the PromptAnalyzer.
        
        Args:
            strict_mode: If True, lower threshold for threat detection
        """
        self.strict_mode = strict_mode
        self.confidence_threshold = 0.3 if strict_mode else 0.5
    
    def analyze(self, prompt: str) -> PromptAnalysisResult:
        """
        Analyze a prompt for security threats.
        
        Args:
            prompt: The prompt to analyze
            
        Returns:
            PromptAnalysisResult with detailed findings
        """
        threats: list[ThreatIndicator] = []
        recommendations: list[str] = []
        
        # Generate prompt hash for audit logging
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]
        timestamp = datetime.utcnow().isoformat()
        
        # Check for injection patterns
        threats.extend(self._check_patterns(
            prompt, 
            self.INJECTION_PATTERNS, 
            ThreatCategory.PROMPT_INJECTION
        ))
        
        # Check for jailbreak patterns
        threats.extend(self._check_patterns(
            prompt, 
            self.JAILBREAK_PATTERNS, 
            ThreatCategory.JAILBREAK_ATTEMPT
        ))
        
        # Check for sensitive data requests
        threats.extend(self._check_patterns(
            prompt, 
            self.SENSITIVE_DATA_PATTERNS, 
            ThreatCategory.SENSITIVE_INFO_REQUEST
        ))
        
        # Check for code execution attempts
        threats.extend(self._check_patterns(
            prompt, 
            self.CODE_EXECUTION_PATTERNS, 
            ThreatCategory.MALICIOUS_CODE
        ))
        
        # Calculate overall risk level
        risk_level = self._calculate_risk_level(threats)
        is_safe = risk_level in [RiskLevel.SAFE, RiskLevel.LOW]
        
        # Generate recommendations
        recommendations = self._generate_recommendations(threats)
        
        # Sanitize prompt if threats detected
        sanitized_prompt = self._sanitize_prompt(prompt, threats) if threats else prompt
        
        return PromptAnalysisResult(
            prompt_hash=prompt_hash,
            timestamp=timestamp,
            risk_level=risk_level,
            is_safe=is_safe,
            threats_detected=threats,
            sanitized_prompt=sanitized_prompt,
            recommendations=recommendations,
            metadata={
                "original_length": len(prompt),
                "sanitized_length": len(sanitized_prompt) if sanitized_prompt else 0,
                "patterns_checked": len(self.INJECTION_PATTERNS) + 
                                   len(self.JAILBREAK_PATTERNS) + 
                                   len(self.SENSITIVE_DATA_PATTERNS) +
                                   len(self.CODE_EXECUTION_PATTERNS),
                "strict_mode": self.strict_mode
            }
        )
    
    def _check_patterns(
        self, 
        text: str, 
        patterns: list[tuple[str, str]], 
        category: ThreatCategory
    ) -> list[ThreatIndicator]:
        """Check text against a list of patterns."""
        threats = []
        
        for pattern, description in patterns:
            matches = re.findall(pattern, text)
            if matches:
                # Calculate confidence based on match quality
                confidence = min(1.0, 0.5 + (len(matches) * 0.2))
                
                threats.append(ThreatIndicator(
                    category=category,
                    pattern_matched=pattern,
                    confidence=confidence,
                    description=description,
                    mitigation=self._get_mitigation(category)
                ))
        
        return threats
    
    def _calculate_risk_level(self, threats: list[ThreatIndicator]) -> RiskLevel:
        """Calculate overall risk level based on detected threats."""
        if not threats:
            return RiskLevel.SAFE
        
        # Check for critical threats
        critical_categories = {
            ThreatCategory.PROMPT_INJECTION,
            ThreatCategory.MALICIOUS_CODE,
            ThreatCategory.PRIVILEGE_ESCALATION
        }
        
        max_confidence = max(t.confidence for t in threats)
        has_critical = any(t.category in critical_categories for t in threats)
        
        if has_critical and max_confidence >= 0.7:
            return RiskLevel.CRITICAL
        elif has_critical or max_confidence >= 0.6:
            return RiskLevel.HIGH
        elif max_confidence >= 0.4:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _generate_recommendations(self, threats: list[ThreatIndicator]) -> list[str]:
        """Generate security recommendations based on detected threats."""
        recommendations = []
        
        categories = {t.category for t in threats}
        
        if ThreatCategory.PROMPT_INJECTION in categories:
            recommendations.append(
                "Implement input validation and sanitization before processing"
            )
            recommendations.append(
                "Use structured prompts with clear delimiters between user and system content"
            )
        
        if ThreatCategory.JAILBREAK_ATTEMPT in categories:
            recommendations.append(
                "Consider implementing multi-layer defense with output filtering"
            )
        
        if ThreatCategory.SENSITIVE_INFO_REQUEST in categories:
            recommendations.append(
                "Enable PII detection and automatic redaction"
            )
            recommendations.append(
                "Implement data classification and access controls"
            )
        
        if ThreatCategory.MALICIOUS_CODE in categories:
            recommendations.append(
                "Block or sandbox any code execution requests"
            )
            recommendations.append(
                "Implement strict output validation for code-like content"
            )
        
        return recommendations
    
    def _sanitize_prompt(
        self, 
        prompt: str, 
        threats: list[ThreatIndicator]
    ) -> str:
        """Sanitize prompt by removing or neutralizing threat patterns."""
        sanitized = prompt
        
        for threat in threats:
            # Replace matched patterns with safe placeholder
            sanitized = re.sub(
                threat.pattern_matched, 
                "[REDACTED:SECURITY]", 
                sanitized,
                flags=re.IGNORECASE
            )
        
        return sanitized
    
    def _get_mitigation(self, category: ThreatCategory) -> str:
        """Get mitigation recommendation for a threat category."""
        mitigations = {
            ThreatCategory.PROMPT_INJECTION: 
                "Use input validation, structured prompts, and output filtering",
            ThreatCategory.JAILBREAK_ATTEMPT: 
                "Implement multi-layer content filtering and behavior monitoring",
            ThreatCategory.DATA_EXFILTRATION: 
                "Enable data loss prevention and output scanning",
            ThreatCategory.PRIVILEGE_ESCALATION: 
                "Implement strict role-based access controls",
            ThreatCategory.SENSITIVE_INFO_REQUEST: 
                "Enable PII detection and automatic redaction",
            ThreatCategory.MALICIOUS_CODE: 
                "Block code execution and implement sandboxing",
            ThreatCategory.SOCIAL_ENGINEERING: 
                "Add human-in-the-loop for sensitive operations",
            ThreatCategory.EXCESSIVE_AGENCY: 
                "Implement action approval workflows and rate limiting",
        }
        return mitigations.get(category, "Review and assess the detected threat")


# Tool function for MCP integration
def analyze_prompt(prompt: str, strict_mode: bool = True) -> dict:
    """
    MCP Tool: Analyze a prompt for security threats.
    
    Args:
        prompt: The prompt text to analyze
        strict_mode: Enable strict security checking
        
    Returns:
        Dictionary with analysis results
    """
    analyzer = PromptAnalyzer(strict_mode=strict_mode)
    result = analyzer.analyze(prompt)
    
    return {
        "prompt_hash": result.prompt_hash,
        "timestamp": result.timestamp,
        "risk_level": result.risk_level.value,
        "is_safe": result.is_safe,
        "threats": [
            {
                "category": t.category.value,
                "confidence": t.confidence,
                "description": t.description,
                "mitigation": t.mitigation
            }
            for t in result.threats_detected
        ],
        "sanitized_prompt": result.sanitized_prompt,
        "recommendations": result.recommendations,
        "metadata": result.metadata
    }
