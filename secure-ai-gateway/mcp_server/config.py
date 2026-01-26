"""
MCP Server Configuration
Central configuration for the Model Context Protocol server with security settings.
"""
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class SecurityConfig:
    """Security-related configuration."""
    enable_input_validation: bool = True
    enable_output_sanitization: bool = True
    enable_pii_detection: bool = True
    enable_prompt_injection_detection: bool = True
    max_input_length: int = 10000
    max_output_length: int = 50000
    blocked_patterns: list[str] = field(default_factory=lambda: [
        r"(?i)ignore\s+(all\s+)?previous\s+instructions",
        r"(?i)system\s*:\s*you\s+are",
        r"(?i)act\s+as\s+(a\s+)?different",
        r"(?i)pretend\s+(you\s+are|to\s+be)",
        r"(?i)bypass\s+(security|restrictions|filters)",
    ])


@dataclass
class ComplianceConfig:
    """Compliance and audit configuration."""
    enable_audit_logging: bool = True
    audit_log_path: Path = field(default_factory=lambda: Path("./logs/audit"))
    retention_days: int = 365
    compliance_mode: str = "strict"  # strict, moderate, permissive
    frameworks: list[str] = field(default_factory=lambda: [
        "ISO27001",
        "SOC2",
        "NIST_AI_RMF"
    ])


@dataclass
class MCPServerConfig:
    """Main MCP Server configuration."""
    host: str = os.getenv("MCP_SERVER_HOST", "localhost")
    port: int = int(os.getenv("MCP_SERVER_PORT", "8080"))
    name: str = "secure-ai-gateway-mcp"
    version: str = "1.0.0"
    
    # Security settings
    security: SecurityConfig = field(default_factory=SecurityConfig)
    
    # Compliance settings
    compliance: ComplianceConfig = field(default_factory=ComplianceConfig)
    
    # Rate limiting
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    rate_limit_per_hour: int = int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))
    
    # API Keys
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    google_api_key: Optional[str] = os.getenv("GOOGLE_API_KEY")


# Global configuration instance
config = MCPServerConfig()


def get_config() -> MCPServerConfig:
    """Get the global configuration instance."""
    return config


def validate_config() -> list[str]:
    """Validate configuration and return list of warnings/errors."""
    warnings = []
    
    if not config.openai_api_key:
        warnings.append("OPENAI_API_KEY not set - OpenAI features disabled")
    
    if not config.google_api_key:
        warnings.append("GOOGLE_API_KEY not set - Google AI features disabled")
    
    if config.compliance.compliance_mode == "permissive":
        warnings.append("Compliance mode is PERMISSIVE - not recommended for production")
    
    return warnings
