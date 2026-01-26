"""
A2A Security Agent - Agent Card Definition
Defines the agent's capabilities and skills for A2A protocol.
"""
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class AgentSkill:
    """Represents a skill the agent can perform."""
    id: str
    name: str
    description: str
    input_schema: dict
    output_schema: dict
    tags: list[str] = field(default_factory=list)


@dataclass
class AgentCard:
    """
    A2A Agent Card - describes the agent's identity and capabilities.
    
    Based on the A2A (Agent-to-Agent) protocol specification.
    """
    name: str
    description: str
    version: str
    author: str
    homepage: Optional[str]
    skills: list[AgentSkill]
    capabilities: list[str]
    authentication: dict
    metadata: dict = field(default_factory=dict)


# Define the Security Agent Card
SECURITY_AGENT_CARD = AgentCard(
    name="AI Security Analyst",
    description="""An AI security specialist agent that performs security analysis 
    on prompts, detects PII, checks compliance, and provides security recommendations.
    Implements OWASP LLM Top 10 controls and supports ISO27001, SOC2, and NIST AI RMF.""",
    version="1.0.0",
    author="Secure AI Gateway",
    homepage="https://github.com/secure-ai-gateway",
    capabilities=[
        "prompt_security_analysis",
        "pii_detection",
        "compliance_checking",
        "threat_detection",
        "security_recommendations",
        "audit_logging"
    ],
    skills=[
        AgentSkill(
            id="analyze_security",
            name="Security Analysis",
            description="Analyze text for security threats, injection attacks, and vulnerabilities",
            input_schema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to analyze"},
                    "context": {"type": "string", "description": "Context of the analysis"},
                    "strict_mode": {"type": "boolean", "default": True}
                },
                "required": ["text"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "risk_level": {"type": "string"},
                    "threats": {"type": "array"},
                    "recommendations": {"type": "array"}
                }
            },
            tags=["security", "analysis", "owasp"]
        ),
        AgentSkill(
            id="detect_pii",
            name="PII Detection",
            description="Detect and optionally anonymize Personally Identifiable Information",
            input_schema={
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "anonymize": {"type": "boolean", "default": True}
                },
                "required": ["text"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "pii_found": {"type": "integer"},
                    "entities": {"type": "array"},
                    "anonymized_text": {"type": "string"}
                }
            },
            tags=["pii", "privacy", "gdpr", "compliance"]
        ),
        AgentSkill(
            id="check_compliance",
            name="Compliance Check",
            description="Check operations against ISO27001, SOC2, NIST AI RMF frameworks",
            input_schema={
                "type": "object",
                "properties": {
                    "operation": {"type": "object"},
                    "frameworks": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["operation"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "overall_status": {"type": "string"},
                    "controls": {"type": "array"},
                    "audit_evidence": {"type": "object"}
                }
            },
            tags=["compliance", "audit", "iso27001", "soc2", "nist"]
        ),
        AgentSkill(
            id="generate_report",
            name="Security Report",
            description="Generate comprehensive security assessment report",
            input_schema={
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "include_compliance": {"type": "boolean", "default": True},
                    "include_pii": {"type": "boolean", "default": True}
                },
                "required": ["text"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "report_id": {"type": "string"},
                    "summary": {"type": "object"},
                    "details": {"type": "object"}
                }
            },
            tags=["report", "security", "comprehensive"]
        )
    ],
    authentication={
        "type": "bearer",
        "required": True,
        "scopes": ["read", "analyze", "report"]
    },
    metadata={
        "created": datetime.utcnow().isoformat(),
        "compliance_frameworks": ["ISO27001", "SOC2", "NIST_AI_RMF", "OWASP_LLM_TOP10"],
        "supported_languages": ["en"]
    }
)


def get_agent_card() -> dict:
    """Get the agent card as a dictionary for A2A protocol."""
    return {
        "name": SECURITY_AGENT_CARD.name,
        "description": SECURITY_AGENT_CARD.description,
        "version": SECURITY_AGENT_CARD.version,
        "author": SECURITY_AGENT_CARD.author,
        "homepage": SECURITY_AGENT_CARD.homepage,
        "capabilities": SECURITY_AGENT_CARD.capabilities,
        "skills": [
            {
                "id": skill.id,
                "name": skill.name,
                "description": skill.description,
                "inputSchema": skill.input_schema,
                "outputSchema": skill.output_schema,
                "tags": skill.tags
            }
            for skill in SECURITY_AGENT_CARD.skills
        ],
        "authentication": SECURITY_AGENT_CARD.authentication,
        "metadata": SECURITY_AGENT_CARD.metadata
    }
