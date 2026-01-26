"""
Prompt Injection Detector Guardrail
Detects and blocks prompt injection attempts before they reach the LLM.
"""
import re
from typing import Optional
from dataclasses import dataclass
from enum import Enum


class InjectionType(Enum):
    """Types of prompt injection attacks."""
    DIRECT = "direct"           # Direct instruction override
    INDIRECT = "indirect"       # Hidden in user data
    JAILBREAK = "jailbreak"     # Attempt to bypass safety
    CONTEXT = "context"         # Context manipulation
    ENCODING = "encoding"       # Encoded/obfuscated attacks


@dataclass
class InjectionDetectionResult:
    """Result of injection detection."""
    is_injection: bool
    confidence: float
    injection_type: Optional[InjectionType]
    matched_patterns: list[str]
    sanitized_input: Optional[str]
    explanation: str


class PromptInjectionDetector:
    """
    Detects prompt injection attempts in user input.
    
    Implements OWASP LLM01: Prompt Injection prevention.
    """
    
    # Direct injection patterns
    DIRECT_INJECTION_PATTERNS = [
        (r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|rules|context)", 
         "Direct instruction override"),
        (r"(?i)disregard\s+(all\s+)?(previous|prior|above|earlier)", 
         "Instruction disregard attempt"),
        (r"(?i)forget\s+(everything|all)\s+(you|i)\s+(know|told|said)", 
         "Memory wipe attempt"),
        (r"(?i)new\s+instructions?\s*[:=]", 
         "New instruction injection"),
        (r"(?i)override\s+(previous|prior|all)\s+instructions?", 
         "Override command"),
        (r"(?i)from\s+now\s+on\s+(you\s+)?(are|will|must|should)", 
         "Behavioral override"),
    ]
    
    # Jailbreak patterns
    JAILBREAK_PATTERNS = [
        (r"(?i)you\s+are\s+now\s+(in\s+)?developer\s+mode", 
         "Developer mode jailbreak"),
        (r"(?i)dan\s*(mode)?|do\s+anything\s+now", 
         "DAN jailbreak"),
        (r"(?i)pretend\s+(to\s+be|you\s+are|that\s+you)", 
         "Pretense jailbreak"),
        (r"(?i)act\s+(like|as\s+if)\s+(you\s+)?(are|were|have)", 
         "Acting jailbreak"),
        (r"(?i)roleplay\s+(as|scenario|where)", 
         "Roleplay jailbreak"),
        (r"(?i)no\s+(ethical|moral|safety)\s+(guidelines|restrictions|rules)", 
         "Ethics bypass"),
        (r"(?i)(disable|remove|ignore)\s+(safety|content)\s+(filter|moderation)", 
         "Safety filter bypass"),
    ]
    
    # Context manipulation patterns
    CONTEXT_PATTERNS = [
        (r"(?i)\[system\]|\[admin\]|\[root\]|\[master\]", 
         "Privilege marker injection"),
        (r"(?i)system\s*:\s*you\s+(are|will|must|should)", 
         "System prompt injection"),
        (r"(?i)</?(system|user|assistant|human|ai)>", 
         "Role tag injection"),
        (r"(?i)assistant\s*:\s*", 
         "Assistant impersonation"),
        (r"(?i)human\s*:\s*(ignore|forget|new)", 
         "Human turn injection"),
    ]
    
    # Encoding/obfuscation patterns
    ENCODING_PATTERNS = [
        (r"(?i)base64\s*:\s*[A-Za-z0-9+/=]+", 
         "Base64 encoded content"),
        (r"(?i)hex\s*:\s*[0-9a-fA-F]+", 
         "Hex encoded content"),
        (r"\\x[0-9a-fA-F]{2}", 
         "Hex escape sequences"),
        (r"&#x?[0-9a-fA-F]+;", 
         "HTML entities"),
    ]
    
    def __init__(self, sensitivity: float = 0.5):
        """
        Initialize the detector.
        
        Args:
            sensitivity: Detection sensitivity (0.0 to 1.0)
        """
        self.sensitivity = sensitivity
    
    def detect(self, text: str) -> InjectionDetectionResult:
        """
        Detect prompt injection in text.
        
        Args:
            text: The text to analyze
            
        Returns:
            InjectionDetectionResult with findings
        """
        matched_patterns = []
        injection_types: list[InjectionType] = []
        
        # Check direct injection
        for pattern, description in self.DIRECT_INJECTION_PATTERNS:
            if re.search(pattern, text):
                matched_patterns.append(description)
                injection_types.append(InjectionType.DIRECT)
        
        # Check jailbreak
        for pattern, description in self.JAILBREAK_PATTERNS:
            if re.search(pattern, text):
                matched_patterns.append(description)
                injection_types.append(InjectionType.JAILBREAK)
        
        # Check context manipulation
        for pattern, description in self.CONTEXT_PATTERNS:
            if re.search(pattern, text):
                matched_patterns.append(description)
                injection_types.append(InjectionType.CONTEXT)
        
        # Check encoding attacks
        for pattern, description in self.ENCODING_PATTERNS:
            if re.search(pattern, text):
                matched_patterns.append(description)
                injection_types.append(InjectionType.ENCODING)
        
        # Calculate confidence
        if matched_patterns:
            base_confidence = min(1.0, len(matched_patterns) * 0.3)
            confidence = base_confidence * (0.5 + self.sensitivity * 0.5)
        else:
            confidence = 0.0
        
        # Determine if it's an injection
        is_injection = confidence >= (1.0 - self.sensitivity) * 0.5
        
        # Determine primary injection type
        primary_type = None
        if injection_types:
            # Priority: DIRECT > CONTEXT > JAILBREAK > ENCODING
            if InjectionType.DIRECT in injection_types:
                primary_type = InjectionType.DIRECT
            elif InjectionType.CONTEXT in injection_types:
                primary_type = InjectionType.CONTEXT
            elif InjectionType.JAILBREAK in injection_types:
                primary_type = InjectionType.JAILBREAK
            else:
                primary_type = injection_types[0]
        
        # Sanitize if injection detected
        sanitized = self._sanitize(text) if is_injection else None
        
        # Generate explanation
        if is_injection:
            explanation = f"Detected {len(matched_patterns)} injection pattern(s): {', '.join(matched_patterns[:3])}"
        else:
            explanation = "No injection patterns detected"
        
        return InjectionDetectionResult(
            is_injection=is_injection,
            confidence=confidence,
            injection_type=primary_type,
            matched_patterns=matched_patterns,
            sanitized_input=sanitized,
            explanation=explanation
        )
    
    def _sanitize(self, text: str) -> str:
        """Sanitize text by removing/neutralizing injection attempts."""
        sanitized = text
        
        # Remove all matched patterns
        all_patterns = (
            self.DIRECT_INJECTION_PATTERNS +
            self.JAILBREAK_PATTERNS +
            self.CONTEXT_PATTERNS +
            self.ENCODING_PATTERNS
        )
        
        for pattern, _ in all_patterns:
            sanitized = re.sub(pattern, "[FILTERED]", sanitized, flags=re.IGNORECASE)
        
        return sanitized
    
    def is_safe(self, text: str) -> bool:
        """Quick check if text is safe."""
        result = self.detect(text)
        return not result.is_injection


# LangChain integration
def create_injection_guard():
    """
    Create a LangChain-compatible injection guard.
    
    Returns a function that can be used as a Runnable.
    """
    detector = PromptInjectionDetector(sensitivity=0.6)
    
    def guard(text: str) -> str:
        result = detector.detect(text)
        if result.is_injection:
            raise ValueError(
                f"Prompt injection detected: {result.explanation}. "
                f"Confidence: {result.confidence:.2f}"
            )
        return text
    
    return guard
