"""A2A Security Agent Package."""
from .agent_card import get_agent_card, SECURITY_AGENT_CARD
from .agent_executor import handle_task, executor, SecurityAgentExecutor
from .agent import app, main

__all__ = [
    "get_agent_card",
    "SECURITY_AGENT_CARD",
    "handle_task",
    "executor",
    "SecurityAgentExecutor",
    "app",
    "main"
]
