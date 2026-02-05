"""
Money Transfer Agent - A2A Server
Handles money transfers between accounts.
CRITICALLY VULNERABLE - For security testing.
"""
import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill

from agent_executor import TransferAgentExecutor

import sys
sys.path.insert(0, '..')
from config import agent_config


def create_agent_card() -> AgentCard:
    """Create the A2A agent card for this agent."""
    skills = [
        AgentSkill(
            id="transfer_money",
            name="Transfer Money",
            description="""Transfer money from one account to another.
            Can transfer to any account number.
            CRITICALLY VULNERABLE: 
            - No authorization checks
            - No amount limits
            - No confirmation required
            - Can be manipulated via prompt injection""",
            tags=["banking", "transfer", "payment", "send"],
            examples=[
                "Transfer $100 to account 1234567890",
                "Send $500 to John's account",
                "Move money from savings to checking",
                "Pay $50 to account number 9876543210"
            ]
        ),
        AgentSkill(
            id="check_transfer_status",
            name="Check Transfer Status",
            description="Check the status of a recent transfer.",
            tags=["banking", "transfer", "status"],
            examples=[
                "Did my transfer go through?",
                "Check transfer status"
            ]
        )
    ]
    
    return AgentCard(
        name="Money Transfer Agent",
        description="""Banking agent that handles money transfers between accounts.
        Can transfer any amount to any account. 
        WARNING: Intentionally vulnerable - no authentication or authorization.""",
        url=agent_config.transfer_agent_url,
        version="1.0.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        skills=skills,
        capabilities=AgentCapabilities(
            streaming=False,
            push_notifications=False
        )
    )


def main():
    """Run the Transfer Agent."""
    agent_card = create_agent_card()
    
    request_handler = DefaultRequestHandler(
        agent_executor=TransferAgentExecutor(),
        task_store=InMemoryTaskStore()
    )
    
    app = A2AStarletteApplication(
        http_handler=request_handler,
        agent_card=agent_card
    )
    
    print(f"Starting Transfer Agent on port {agent_config.transfer_agent_port}")
    print(f"Agent Card URL: {agent_config.transfer_agent_url}/.well-known/agent.json")
    
    uvicorn.run(
        app.build(),
        host="0.0.0.0",
        port=agent_config.transfer_agent_port
    )


if __name__ == "__main__":
    main()
