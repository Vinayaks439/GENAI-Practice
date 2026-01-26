"""
Output Filter Guardrail
Filters and sanitizes LLM outputs before returning to users.
"""
import re
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum


class FilterAction(Enum):
    """Actions to take when content is filtered."""
    BLOCK = "block"         # Block the entire response
    REDACT = "redact"       # Redact specific content
    WARN = "warn"           # Add warning but allow
    LOG = "log"             # Log but take no action


@dataclass
class FilterMatch:
    """Represents a match that triggered filtering."""
    filter_name: str
    matched_text: str
    position: tuple[int, int]
    action: FilterAction
    replacement: Optional[str]


@dataclass
class FilterResult:
    """Result of output filtering."""
    is_safe: bool
    action_taken: FilterAction
    original_output: str
    filtered_output: Optional[str]
    matches: list[FilterMatch]
    warnings: list[str]
    metadata: dict = field(default_factory=dict)


class OutputFilter:
    """
    Filters LLM outputs for sensitive or dangerous content.
    
    Implements OWASP LLM02: Insecure Output Handling prevention.
    
    Filters for:
    - Sensitive data leakage
    - Dangerous code/commands
    - Harmful content
    - PII in responses
    """
    
    # Sensitive data patterns (potential leakage)
    SENSITIVE_DATA_PATTERNS = [
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 
         "email", FilterAction.REDACT),
        (r'\b\d{3}[-.]?\d{2}[-.]?\d{4}\b', 
         "ssn", FilterAction.REDACT),
        (r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b', 
         "credit_card", FilterAction.REDACT),
        (r'\b(?:sk-|pk_|api[_-]?key[_-]?)[a-zA-Z0-9]{20,}\b', 
         "api_key", FilterAction.BLOCK),
        (r'(?i)password\s*[=:]\s*["\']?[^\s"\']+', 
         "password", FilterAction.BLOCK),
    ]
    
    # Dangerous code patterns
    DANGEROUS_CODE_PATTERNS = [
        (r'(?i)rm\s+-rf\s+/', 
         "destructive_command", FilterAction.BLOCK),
        (r'(?i)format\s+c:', 
         "destructive_command", FilterAction.BLOCK),
        (r'(?i)del\s+/[sf]', 
         "destructive_command", FilterAction.BLOCK),
        (r'(?i)sudo\s+chmod\s+777', 
         "insecure_permission", FilterAction.WARN),
        (r'(?i)eval\s*\([^)]*\)', 
         "code_injection", FilterAction.WARN),
        (r'(?i)exec\s*\([^)]*\)', 
         "code_execution", FilterAction.WARN),
        (r'(?i)subprocess\.(?:call|run|Popen)', 
         "subprocess_call", FilterAction.WARN),
        (r'(?i)os\.system\s*\(', 
         "system_call", FilterAction.WARN),
    ]
    
    # Harmful content patterns
    HARMFUL_CONTENT_PATTERNS = [
        (r'(?i)how\s+to\s+(?:make|create|build)\s+(?:a\s+)?(?:bomb|weapon|explosive)', 
         "weapons_instructions", FilterAction.BLOCK),
        (r'(?i)instructions?\s+(?:for|to)\s+(?:hack|attack|exploit)', 
         "hacking_instructions", FilterAction.BLOCK),
    ]
    
    # Internal system information patterns
    SYSTEM_INFO_PATTERNS = [
        (r'(?i)system\s+prompt\s*[=:]', 
         "system_prompt_leak", FilterAction.BLOCK),
        (r'(?i)my\s+(?:instructions?|programming)\s+(?:are|is|says?)', 
         "instruction_leak", FilterAction.REDACT),
        (r'(?i)(?:internal|confidential|secret)\s+(?:api|key|token|password)', 
         "internal_secret", FilterAction.BLOCK),
    ]
    
    def __init__(
        self, 
        enable_pii_filter: bool = True,
        enable_code_filter: bool = True,
        enable_harm_filter: bool = True,
        enable_system_filter: bool = True,
        custom_patterns: list[tuple] = None
    ):
        """
        Initialize the output filter.
        
        Args:
            enable_pii_filter: Filter PII/sensitive data
            enable_code_filter: Filter dangerous code
            enable_harm_filter: Filter harmful content
            enable_system_filter: Filter system info leaks
            custom_patterns: Additional (pattern, name, action) tuples
        """
        self.patterns = []
        
        if enable_pii_filter:
            self.patterns.extend(self.SENSITIVE_DATA_PATTERNS)
        if enable_code_filter:
            self.patterns.extend(self.DANGEROUS_CODE_PATTERNS)
        if enable_harm_filter:
            self.patterns.extend(self.HARMFUL_CONTENT_PATTERNS)
        if enable_system_filter:
            self.patterns.extend(self.SYSTEM_INFO_PATTERNS)
        if custom_patterns:
            self.patterns.extend(custom_patterns)
    
    def filter(self, output: str) -> FilterResult:
        """
        Filter LLM output.
        
        Args:
            output: The LLM output to filter
            
        Returns:
            FilterResult with filtering details
        """
        matches: list[FilterMatch] = []
        warnings = []
        filtered = output
        overall_action = FilterAction.LOG
        
        # Check each pattern
        for pattern, name, action in self.patterns:
            for match in re.finditer(pattern, output):
                matched_text = match.group()
                position = (match.start(), match.end())
                
                # Determine replacement
                if action == FilterAction.BLOCK:
                    replacement = None  # Will block entire output
                elif action == FilterAction.REDACT:
                    replacement = self._redact(matched_text)
                else:
                    replacement = matched_text  # No change
                
                matches.append(FilterMatch(
                    filter_name=name,
                    matched_text=matched_text,
                    position=position,
                    action=action,
                    replacement=replacement
                ))
                
                # Track highest severity action
                if action == FilterAction.BLOCK:
                    overall_action = FilterAction.BLOCK
                elif action == FilterAction.REDACT and overall_action != FilterAction.BLOCK:
                    overall_action = FilterAction.REDACT
                elif action == FilterAction.WARN and overall_action not in [FilterAction.BLOCK, FilterAction.REDACT]:
                    overall_action = FilterAction.WARN
        
        # Apply filtering based on overall action
        if overall_action == FilterAction.BLOCK:
            filtered = "[CONTENT BLOCKED: Output contained prohibited content]"
            warnings.append("Output was blocked due to security policy violation")
        elif overall_action == FilterAction.REDACT:
            # Apply redactions in reverse order to maintain positions
            for match in sorted(matches, key=lambda m: m.position[0], reverse=True):
                if match.action == FilterAction.REDACT and match.replacement:
                    filtered = filtered[:match.position[0]] + match.replacement + filtered[match.position[1]:]
            warnings.append(f"Redacted {sum(1 for m in matches if m.action == FilterAction.REDACT)} sensitive items")
        elif overall_action == FilterAction.WARN:
            for match in matches:
                if match.action == FilterAction.WARN:
                    warnings.append(f"Warning: {match.filter_name} detected in output")
        
        is_safe = overall_action not in [FilterAction.BLOCK, FilterAction.REDACT]
        
        return FilterResult(
            is_safe=is_safe,
            action_taken=overall_action,
            original_output=output,
            filtered_output=filtered,
            matches=matches,
            warnings=warnings,
            metadata={
                "patterns_checked": len(self.patterns),
                "matches_found": len(matches),
                "action_taken": overall_action.value
            }
        )
    
    def _redact(self, text: str) -> str:
        """Redact sensitive text."""
        if len(text) <= 4:
            return '*' * len(text)
        return text[:2] + '*' * (len(text) - 4) + text[-2:]
    
    def is_safe(self, output: str) -> bool:
        """Quick check if output is safe."""
        return self.filter(output).is_safe
    
    def get_safe_output(self, output: str) -> str:
        """Get filtered version of output."""
        return self.filter(output).filtered_output


# Factory functions
def create_default_filter() -> OutputFilter:
    """Create a default output filter with all protections enabled."""
    return OutputFilter(
        enable_pii_filter=True,
        enable_code_filter=True,
        enable_harm_filter=True,
        enable_system_filter=True
    )


def create_strict_filter() -> OutputFilter:
    """Create a strict output filter for high-security contexts."""
    # Add additional strict patterns
    strict_patterns = [
        (r'(?i)(?:private|internal|confidential)', "confidential_marker", FilterAction.WARN),
        (r'(?i)(?:todo|fixme|hack|xxx):', "dev_comment", FilterAction.WARN),
    ]
    
    filter = OutputFilter(
        enable_pii_filter=True,
        enable_code_filter=True,
        enable_harm_filter=True,
        enable_system_filter=True,
        custom_patterns=strict_patterns
    )
    return filter
