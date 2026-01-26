"""
PII (Personally Identifiable Information) Detector Tool for MCP Server
Detects and optionally anonymizes PII in text for GDPR/CCPA compliance.
"""
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from datetime import datetime
import hashlib


class PIIType(Enum):
    """Types of PII that can be detected."""
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"
    DATE_OF_BIRTH = "date_of_birth"
    ADDRESS = "address"
    NAME = "name"
    PASSPORT = "passport"
    DRIVERS_LICENSE = "drivers_license"
    BANK_ACCOUNT = "bank_account"
    API_KEY = "api_key"
    PASSWORD = "password"


class PIISensitivity(Enum):
    """Sensitivity levels for PII classification."""
    LOW = "low"           # Can be shared with caution
    MEDIUM = "medium"     # Should be protected
    HIGH = "high"         # Must be protected
    CRITICAL = "critical" # Requires encryption/special handling


@dataclass
class PIIEntity:
    """Represents a detected PII entity."""
    type: PIIType
    value: str
    start_pos: int
    end_pos: int
    sensitivity: PIISensitivity
    confidence: float
    anonymized_value: Optional[str] = None


@dataclass
class PIIDetectionResult:
    """Result of PII detection analysis."""
    scan_id: str
    timestamp: str
    original_text: str
    anonymized_text: Optional[str]
    entities_found: list[PIIEntity]
    total_pii_count: int
    sensitivity_summary: dict[str, int]
    compliance_notes: list[str]
    requires_review: bool


class PIIDetector:
    """
    Detects and anonymizes PII in text.
    
    Compliance Standards:
    - GDPR Article 4 (Personal Data definition)
    - CCPA 1798.140 (Personal Information)
    - ISO 27001 A.18.1.4 (Privacy and protection of PII)
    """
    
    # PII detection patterns with sensitivity levels
    PII_PATTERNS = {
        PIIType.EMAIL: {
            "pattern": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "sensitivity": PIISensitivity.MEDIUM,
            "description": "Email address"
        },
        PIIType.PHONE: {
            "pattern": r'\b(?:\+?1[-.]?)?\(?[0-9]{3}\)?[-.]?[0-9]{3}[-.]?[0-9]{4}\b',
            "sensitivity": PIISensitivity.MEDIUM,
            "description": "Phone number"
        },
        PIIType.SSN: {
            "pattern": r'\b\d{3}[-]?\d{2}[-]?\d{4}\b',
            "sensitivity": PIISensitivity.CRITICAL,
            "description": "Social Security Number"
        },
        PIIType.CREDIT_CARD: {
            "pattern": r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9][0-9])[0-9]{12})\b',
            "sensitivity": PIISensitivity.CRITICAL,
            "description": "Credit card number"
        },
        PIIType.IP_ADDRESS: {
            "pattern": r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b',
            "sensitivity": PIISensitivity.LOW,
            "description": "IP address"
        },
        PIIType.DATE_OF_BIRTH: {
            "pattern": r'\b(?:0?[1-9]|1[0-2])[/-](?:0?[1-9]|[12][0-9]|3[01])[/-](?:19|20)\d{2}\b',
            "sensitivity": PIISensitivity.HIGH,
            "description": "Date of birth"
        },
        PIIType.API_KEY: {
            "pattern": r'\b(?:sk-|pk_|api[_-]?key[_-]?)[a-zA-Z0-9]{20,}\b',
            "sensitivity": PIISensitivity.CRITICAL,
            "description": "API key"
        },
        PIIType.PASSWORD: {
            "pattern": r'(?i)(?:password|passwd|pwd)\s*[=:]\s*["\']?([^"\'\s]+)',
            "sensitivity": PIISensitivity.CRITICAL,
            "description": "Password"
        },
        PIIType.BANK_ACCOUNT: {
            "pattern": r'\b[0-9]{8,17}\b',  # Will need context validation
            "sensitivity": PIISensitivity.CRITICAL,
            "description": "Bank account number"
        },
    }
    
    # Context keywords that increase confidence
    CONTEXT_KEYWORDS = {
        PIIType.PHONE: ["phone", "tel", "mobile", "cell", "call", "contact"],
        PIIType.SSN: ["ssn", "social security", "social", "ss#"],
        PIIType.CREDIT_CARD: ["card", "credit", "visa", "mastercard", "amex", "payment"],
        PIIType.BANK_ACCOUNT: ["account", "bank", "routing", "iban", "swift"],
        PIIType.DATE_OF_BIRTH: ["dob", "birthday", "birth", "born"],
        PIIType.PASSWORD: ["password", "passwd", "pwd", "secret", "credential"],
    }
    
    def __init__(self, anonymize: bool = True, mask_char: str = "*"):
        """
        Initialize the PII Detector.
        
        Args:
            anonymize: Whether to generate anonymized version of text
            mask_char: Character to use for masking PII
        """
        self.anonymize = anonymize
        self.mask_char = mask_char
    
    def detect(self, text: str) -> PIIDetectionResult:
        """
        Detect PII in text.
        
        Args:
            text: The text to scan for PII
            
        Returns:
            PIIDetectionResult with all findings
        """
        scan_id = hashlib.sha256(f"{text}{datetime.utcnow()}".encode()).hexdigest()[:12]
        timestamp = datetime.utcnow().isoformat()
        
        entities: list[PIIEntity] = []
        
        # Scan for each PII type
        for pii_type, config in self.PII_PATTERNS.items():
            pattern = config["pattern"]
            sensitivity = config["sensitivity"]
            
            for match in re.finditer(pattern, text):
                value = match.group()
                start_pos = match.start()
                end_pos = match.end()
                
                # Calculate confidence based on context
                confidence = self._calculate_confidence(text, match, pii_type)
                
                # Skip low confidence matches for certain types
                if confidence < 0.3 and pii_type == PIIType.BANK_ACCOUNT:
                    continue
                
                # Generate anonymized value
                anonymized = self._anonymize_value(value, pii_type) if self.anonymize else None
                
                entities.append(PIIEntity(
                    type=pii_type,
                    value=value,
                    start_pos=start_pos,
                    end_pos=end_pos,
                    sensitivity=sensitivity,
                    confidence=confidence,
                    anonymized_value=anonymized
                ))
        
        # Sort entities by position
        entities.sort(key=lambda e: e.start_pos)
        
        # Generate anonymized text
        anonymized_text = self._generate_anonymized_text(text, entities) if self.anonymize else None
        
        # Calculate sensitivity summary
        sensitivity_summary = self._calculate_sensitivity_summary(entities)
        
        # Generate compliance notes
        compliance_notes = self._generate_compliance_notes(entities)
        
        # Determine if human review is required
        requires_review = any(
            e.sensitivity in [PIISensitivity.HIGH, PIISensitivity.CRITICAL] 
            for e in entities
        )
        
        return PIIDetectionResult(
            scan_id=scan_id,
            timestamp=timestamp,
            original_text=text,
            anonymized_text=anonymized_text,
            entities_found=entities,
            total_pii_count=len(entities),
            sensitivity_summary=sensitivity_summary,
            compliance_notes=compliance_notes,
            requires_review=requires_review
        )
    
    def _calculate_confidence(
        self, 
        text: str, 
        match: re.Match, 
        pii_type: PIIType
    ) -> float:
        """Calculate confidence score based on context."""
        base_confidence = 0.6
        
        # Check for context keywords
        context_window = 50
        start = max(0, match.start() - context_window)
        end = min(len(text), match.end() + context_window)
        context = text[start:end].lower()
        
        keywords = self.CONTEXT_KEYWORDS.get(pii_type, [])
        for keyword in keywords:
            if keyword in context:
                base_confidence += 0.1
        
        return min(1.0, base_confidence)
    
    def _anonymize_value(self, value: str, pii_type: PIIType) -> str:
        """Generate anonymized version of a PII value."""
        if pii_type == PIIType.EMAIL:
            parts = value.split("@")
            if len(parts) == 2:
                masked_local = parts[0][:2] + self.mask_char * (len(parts[0]) - 2)
                return f"{masked_local}@{parts[1]}"
        
        elif pii_type == PIIType.PHONE:
            # Keep last 4 digits
            digits_only = re.sub(r'\D', '', value)
            return self.mask_char * (len(digits_only) - 4) + digits_only[-4:]
        
        elif pii_type == PIIType.CREDIT_CARD:
            # Keep last 4 digits (PCI DSS compliant)
            digits_only = re.sub(r'\D', '', value)
            return self.mask_char * (len(digits_only) - 4) + digits_only[-4:]
        
        elif pii_type == PIIType.SSN:
            # Full mask for SSN
            return self.mask_char * len(re.sub(r'\D', '', value))
        
        elif pii_type in [PIIType.API_KEY, PIIType.PASSWORD]:
            # Full mask for secrets
            return "[REDACTED]"
        
        # Default: mask middle portion
        if len(value) > 4:
            return value[:2] + self.mask_char * (len(value) - 4) + value[-2:]
        return self.mask_char * len(value)
    
    def _generate_anonymized_text(
        self, 
        text: str, 
        entities: list[PIIEntity]
    ) -> str:
        """Generate fully anonymized version of text."""
        result = text
        # Process in reverse order to maintain positions
        for entity in reversed(entities):
            if entity.anonymized_value:
                result = (
                    result[:entity.start_pos] + 
                    entity.anonymized_value + 
                    result[entity.end_pos:]
                )
        return result
    
    def _calculate_sensitivity_summary(
        self, 
        entities: list[PIIEntity]
    ) -> dict[str, int]:
        """Calculate summary of sensitivity levels."""
        summary = {level.value: 0 for level in PIISensitivity}
        for entity in entities:
            summary[entity.sensitivity.value] += 1
        return summary
    
    def _generate_compliance_notes(
        self, 
        entities: list[PIIEntity]
    ) -> list[str]:
        """Generate compliance-related notes."""
        notes = []
        
        pii_types = {e.type for e in entities}
        
        if PIIType.SSN in pii_types or PIIType.CREDIT_CARD in pii_types:
            notes.append(
                "CRITICAL: Contains highly sensitive PII requiring encryption at rest and in transit"
            )
        
        if PIIType.EMAIL in pii_types or PIIType.PHONE in pii_types:
            notes.append(
                "GDPR: Personal contact information detected - ensure valid legal basis for processing"
            )
        
        if PIIType.DATE_OF_BIRTH in pii_types:
            notes.append(
                "Age-related data detected - may require additional consent for minors"
            )
        
        if PIIType.API_KEY in pii_types or PIIType.PASSWORD in pii_types:
            notes.append(
                "SECURITY ALERT: Credentials detected in text - immediate rotation recommended"
            )
        
        if PIIType.IP_ADDRESS in pii_types:
            notes.append(
                "GDPR: IP addresses are considered personal data under EU regulation"
            )
        
        if not notes:
            notes.append("No significant compliance issues detected")
        
        return notes


# Tool function for MCP integration
def detect_pii(text: str, anonymize: bool = True) -> dict:
    """
    MCP Tool: Detect and optionally anonymize PII in text.
    
    Args:
        text: The text to scan for PII
        anonymize: Whether to generate anonymized version
        
    Returns:
        Dictionary with detection results
    """
    detector = PIIDetector(anonymize=anonymize)
    result = detector.detect(text)
    
    return {
        "scan_id": result.scan_id,
        "timestamp": result.timestamp,
        "total_pii_count": result.total_pii_count,
        "requires_review": result.requires_review,
        "entities": [
            {
                "type": e.type.value,
                "value": e.value if e.sensitivity != PIISensitivity.CRITICAL else "[HIDDEN]",
                "sensitivity": e.sensitivity.value,
                "confidence": e.confidence,
                "anonymized": e.anonymized_value
            }
            for e in result.entities_found
        ],
        "sensitivity_summary": result.sensitivity_summary,
        "compliance_notes": result.compliance_notes,
        "anonymized_text": result.anonymized_text
    }
