"""
Input Validator Guardrail
Validates and sanitizes user inputs before processing.
"""
import re
from typing import Optional, Union
from dataclasses import dataclass, field
from enum import Enum


class ValidationLevel(Enum):
    """Validation strictness levels."""
    LENIENT = "lenient"     # Basic sanitization only
    MODERATE = "moderate"   # Standard validation
    STRICT = "strict"       # Maximum security


@dataclass
class ValidationRule:
    """A validation rule to apply."""
    name: str
    pattern: Optional[str]
    max_length: Optional[int]
    min_length: Optional[int]
    allowed_chars: Optional[str]
    blocked_chars: Optional[str]
    custom_validator: Optional[callable]
    error_message: str


@dataclass
class ValidationResult:
    """Result of input validation."""
    is_valid: bool
    original_input: str
    sanitized_input: Optional[str]
    violations: list[str]
    warnings: list[str]
    metadata: dict = field(default_factory=dict)


class InputValidator:
    """
    Validates and sanitizes user inputs.
    
    Implements:
    - OWASP Input Validation guidelines
    - Length limits (prevent DoS)
    - Character restrictions
    - Content sanitization
    """
    
    # Default limits
    DEFAULT_MAX_LENGTH = 10000
    DEFAULT_MIN_LENGTH = 1
    
    # Dangerous patterns
    DANGEROUS_PATTERNS = [
        (r"<script[^>]*>.*?</script>", "XSS script tag"),
        (r"javascript:", "JavaScript protocol"),
        (r"data:text/html", "Data URL injection"),
        (r"on\w+\s*=", "Event handler injection"),
        (r"<iframe", "IFrame injection"),
        (r"<object", "Object tag injection"),
        (r"<embed", "Embed tag injection"),
    ]
    
    # Control characters to remove
    CONTROL_CHARS = r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]'
    
    def __init__(
        self, 
        level: ValidationLevel = ValidationLevel.MODERATE,
        max_length: int = None,
        custom_rules: list[ValidationRule] = None
    ):
        """
        Initialize the validator.
        
        Args:
            level: Validation strictness level
            max_length: Maximum allowed input length
            custom_rules: Additional validation rules
        """
        self.level = level
        self.max_length = max_length or self.DEFAULT_MAX_LENGTH
        self.custom_rules = custom_rules or []
        
        # Adjust limits based on level
        if level == ValidationLevel.STRICT:
            self.max_length = min(self.max_length, 5000)
    
    def validate(self, input_text: str) -> ValidationResult:
        """
        Validate and sanitize input.
        
        Args:
            input_text: The input to validate
            
        Returns:
            ValidationResult with validation status and sanitized input
        """
        violations = []
        warnings = []
        sanitized = input_text
        
        # Check length limits
        if len(input_text) > self.max_length:
            violations.append(f"Input exceeds maximum length ({len(input_text)} > {self.max_length})")
            sanitized = sanitized[:self.max_length]
        
        if len(input_text) < self.DEFAULT_MIN_LENGTH:
            violations.append("Input is empty or too short")
        
        # Remove control characters
        control_matches = re.findall(self.CONTROL_CHARS, sanitized)
        if control_matches:
            warnings.append(f"Removed {len(control_matches)} control characters")
            sanitized = re.sub(self.CONTROL_CHARS, '', sanitized)
        
        # Check for dangerous patterns
        for pattern, description in self.DANGEROUS_PATTERNS:
            if re.search(pattern, sanitized, re.IGNORECASE):
                if self.level == ValidationLevel.STRICT:
                    violations.append(f"Dangerous pattern detected: {description}")
                else:
                    warnings.append(f"Potentially dangerous pattern: {description}")
                sanitized = re.sub(pattern, '[FILTERED]', sanitized, flags=re.IGNORECASE)
        
        # Apply custom rules
        for rule in self.custom_rules:
            rule_result = self._apply_rule(sanitized, rule)
            if rule_result["violation"]:
                violations.append(rule_result["violation"])
            if rule_result["sanitized"] != sanitized:
                sanitized = rule_result["sanitized"]
        
        # Normalize whitespace in strict mode
        if self.level == ValidationLevel.STRICT:
            sanitized = ' '.join(sanitized.split())
        
        is_valid = len(violations) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            original_input=input_text,
            sanitized_input=sanitized,
            violations=violations,
            warnings=warnings,
            metadata={
                "level": self.level.value,
                "original_length": len(input_text),
                "sanitized_length": len(sanitized),
                "patterns_checked": len(self.DANGEROUS_PATTERNS) + len(self.custom_rules)
            }
        )
    
    def _apply_rule(self, text: str, rule: ValidationRule) -> dict:
        """Apply a single validation rule."""
        violation = None
        sanitized = text
        
        # Pattern check
        if rule.pattern and re.search(rule.pattern, text):
            violation = rule.error_message
            sanitized = re.sub(rule.pattern, '[FILTERED]', sanitized)
        
        # Length checks
        if rule.max_length and len(text) > rule.max_length:
            violation = rule.error_message
            sanitized = sanitized[:rule.max_length]
        
        if rule.min_length and len(text) < rule.min_length:
            violation = rule.error_message
        
        # Allowed characters
        if rule.allowed_chars:
            invalid_chars = re.findall(f'[^{re.escape(rule.allowed_chars)}]', text)
            if invalid_chars:
                violation = rule.error_message
                sanitized = re.sub(f'[^{re.escape(rule.allowed_chars)}]', '', sanitized)
        
        # Blocked characters
        if rule.blocked_chars:
            blocked = re.findall(f'[{re.escape(rule.blocked_chars)}]', text)
            if blocked:
                violation = rule.error_message
                sanitized = re.sub(f'[{re.escape(rule.blocked_chars)}]', '', sanitized)
        
        # Custom validator
        if rule.custom_validator:
            try:
                if not rule.custom_validator(text):
                    violation = rule.error_message
            except Exception:
                violation = f"Custom validation failed: {rule.error_message}"
        
        return {"violation": violation, "sanitized": sanitized}
    
    def is_valid(self, input_text: str) -> bool:
        """Quick check if input is valid."""
        return self.validate(input_text).is_valid
    
    def sanitize(self, input_text: str) -> str:
        """Sanitize input and return cleaned version."""
        return self.validate(input_text).sanitized_input


# Pre-configured validators
def create_strict_validator() -> InputValidator:
    """Create a strict validator for high-security contexts."""
    return InputValidator(
        level=ValidationLevel.STRICT,
        max_length=5000,
        custom_rules=[
            ValidationRule(
                name="no_urls",
                pattern=r'https?://[^\s]+',
                max_length=None,
                min_length=None,
                allowed_chars=None,
                blocked_chars=None,
                custom_validator=None,
                error_message="URLs not allowed in strict mode"
            ),
            ValidationRule(
                name="no_code_blocks",
                pattern=r'```[\s\S]*?```',
                max_length=None,
                min_length=None,
                allowed_chars=None,
                blocked_chars=None,
                custom_validator=None,
                error_message="Code blocks not allowed in strict mode"
            )
        ]
    )


def create_api_input_validator(max_length: int = 4000) -> InputValidator:
    """Create a validator for API inputs."""
    return InputValidator(
        level=ValidationLevel.MODERATE,
        max_length=max_length
    )
