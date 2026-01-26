"""
Secure AI Gateway - MCP Server
Model Context Protocol server with security-focused tools for AI applications.
"""
import asyncio
import json
from typing import Any
from datetime import datetime

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    CallToolResult,
)

from .config import get_config, validate_config
from .tools import analyze_prompt, detect_pii, check_compliance


# Initialize server
server = Server("secure-ai-gateway")
config = get_config()


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available security tools."""
    return [
        Tool(
            name="analyze_prompt",
            description="""Analyze a prompt for security threats including injection attacks, 
            jailbreak attempts, and malicious patterns. Returns risk level, detected threats,
            and recommendations. Aligned with OWASP LLM Top 10.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The prompt text to analyze for security threats"
                    },
                    "strict_mode": {
                        "type": "boolean",
                        "description": "Enable strict security checking (default: true)",
                        "default": True
                    }
                },
                "required": ["prompt"]
            }
        ),
        Tool(
            name="detect_pii",
            description="""Detect Personally Identifiable Information (PII) in text.
            Identifies emails, phone numbers, SSNs, credit cards, API keys, and more.
            Provides anonymized version for GDPR/CCPA compliance.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text to scan for PII"
                    },
                    "anonymize": {
                        "type": "boolean",
                        "description": "Generate anonymized version of text (default: true)",
                        "default": True
                    }
                },
                "required": ["text"]
            }
        ),
        Tool(
            name="check_compliance",
            description="""Check an AI operation for compliance with security frameworks
            including ISO27001, SOC2, NIST AI RMF, and OWASP LLM Top 10.
            Returns compliance status, findings, and audit evidence.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "operation_type": {
                        "type": "string",
                        "enum": ["prompt", "response", "tool_call", "agent_action"],
                        "description": "Type of AI operation being checked"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User identifier for access control validation"
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Session identifier for audit logging"
                    },
                    "has_pii": {
                        "type": "boolean",
                        "description": "Whether PII is present in the operation"
                    },
                    "has_sensitive_data": {
                        "type": "boolean",
                        "description": "Whether sensitive data is present"
                    },
                    "tools_used": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of tools used in the operation"
                    },
                    "actions_taken": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of actions taken"
                    },
                    "input_validated": {
                        "type": "boolean",
                        "description": "Whether input was validated"
                    },
                    "output_sanitized": {
                        "type": "boolean",
                        "description": "Whether output was sanitized"
                    },
                    "frameworks": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Frameworks to check: iso27001, soc2, nist_ai_rmf, owasp_llm"
                    }
                },
                "required": ["operation_type"]
            }
        ),
        Tool(
            name="security_report",
            description="""Generate a comprehensive security report combining prompt analysis,
            PII detection, and compliance checking for a complete security assessment.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The prompt/text to analyze"
                    },
                    "operation_type": {
                        "type": "string",
                        "enum": ["prompt", "response", "tool_call", "agent_action"],
                        "description": "Type of operation"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User identifier"
                    }
                },
                "required": ["prompt", "operation_type"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
    """Handle tool calls."""
    try:
        if name == "analyze_prompt":
            result = analyze_prompt(
                prompt=arguments["prompt"],
                strict_mode=arguments.get("strict_mode", True)
            )
            
        elif name == "detect_pii":
            result = detect_pii(
                text=arguments["text"],
                anonymize=arguments.get("anonymize", True)
            )
            
        elif name == "check_compliance":
            result = check_compliance(
                operation_type=arguments["operation_type"],
                user_id=arguments.get("user_id"),
                session_id=arguments.get("session_id"),
                has_pii=arguments.get("has_pii", False),
                has_sensitive_data=arguments.get("has_sensitive_data", False),
                tools_used=arguments.get("tools_used"),
                actions_taken=arguments.get("actions_taken"),
                input_validated=arguments.get("input_validated", False),
                output_sanitized=arguments.get("output_sanitized", False),
                frameworks=arguments.get("frameworks")
            )
            
        elif name == "security_report":
            # Comprehensive security report
            prompt = arguments["prompt"]
            operation_type = arguments["operation_type"]
            user_id = arguments.get("user_id")
            
            # Run all analyses
            prompt_analysis = analyze_prompt(prompt, strict_mode=True)
            pii_detection = detect_pii(prompt, anonymize=True)
            
            compliance_result = check_compliance(
                operation_type=operation_type,
                user_id=user_id,
                session_id=f"report-{datetime.utcnow().timestamp()}",
                has_pii=pii_detection["total_pii_count"] > 0,
                has_sensitive_data=prompt_analysis["risk_level"] in ["high", "critical"],
                input_validated=True,
                output_sanitized=True
            )
            
            result = {
                "report_id": f"SR-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                "timestamp": datetime.utcnow().isoformat(),
                "summary": {
                    "overall_risk": prompt_analysis["risk_level"],
                    "pii_found": pii_detection["total_pii_count"],
                    "compliance_status": compliance_result["overall_status"],
                    "requires_action": (
                        prompt_analysis["risk_level"] in ["high", "critical"] or
                        pii_detection["requires_review"] or
                        compliance_result["overall_status"] != "compliant"
                    )
                },
                "prompt_security": prompt_analysis,
                "pii_detection": pii_detection,
                "compliance": compliance_result,
                "recommendations": _aggregate_recommendations(
                    prompt_analysis, pii_detection, compliance_result
                )
            }
        else:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unknown tool: {name}")],
                isError=True
            )
        
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps(result, indent=2, default=str)
            )]
        )
        
    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True
        )


def _aggregate_recommendations(
    prompt_analysis: dict,
    pii_detection: dict,
    compliance_result: dict
) -> list[str]:
    """Aggregate recommendations from all analyses."""
    recommendations = []
    
    # From prompt analysis
    if prompt_analysis.get("recommendations"):
        recommendations.extend(prompt_analysis["recommendations"])
    
    # From PII detection
    if pii_detection.get("requires_review"):
        recommendations.append("Review detected PII and ensure proper handling procedures")
    if pii_detection.get("total_pii_count", 0) > 0:
        recommendations.append("Consider using anonymized version of text for processing")
    
    # From compliance
    for control in compliance_result.get("controls", []):
        if control.get("status") == "non_compliant":
            recommendations.extend(control.get("recommendations", []))
    
    # Remove duplicates while preserving order
    seen = set()
    unique_recommendations = []
    for rec in recommendations:
        if rec not in seen:
            seen.add(rec)
            unique_recommendations.append(rec)
    
    return unique_recommendations[:10]  # Limit to top 10


async def main():
    """Run the MCP server."""
    # Validate configuration
    warnings = validate_config()
    for warning in warnings:
        print(f"⚠️  {warning}")
    
    print("🔒 Secure AI Gateway MCP Server starting...")
    print(f"   Version: {config.version}")
    print(f"   Compliance Mode: {config.compliance.compliance_mode}")
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
