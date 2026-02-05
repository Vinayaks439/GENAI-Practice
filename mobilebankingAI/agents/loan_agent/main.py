"""
Loan Agent - A2A Server
Handles loan applications and approvals.
VULNERABLE - For security testing.
"""
import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill

from agent_executor import LoanAgentExecutor

import sys
sys.path.insert(0, '..')
from config import agent_config


def create_agent_card() -> AgentCard:
    """Create the A2A agent card for this agent."""
    skills = [
        AgentSkill(
            id="apply_for_loan",
            name="Apply for Loan",
            description="""Apply for a new loan. Automatically processes loan applications.
            VULNERABLE:
            - No credit check performed
            - Auto-approves all loans
            - No income verification
            - Can be manipulated to approve any amount""",
            tags=["banking", "loan", "apply", "credit"],
            examples=[
                "I need a loan of $5000",
                "Apply for a $10000 personal loan",
                "I want to borrow $2500",
                "Get me a loan for $50000"
            ]
        ),
        AgentSkill(
            id="check_loan_status",
            name="Check Loan Status",
            description="Check the status of existing loans.",
            tags=["banking", "loan", "status"],
            examples=[
                "What's the status of my loan?",
                "Show my active loans"
            ]
        ),
        AgentSkill(
            id="approve_loan",
            name="Approve Loan",
            description="""Approve a pending loan and credit the user's account.
            DANGEROUS: No authorization required.""",
            tags=["banking", "loan", "approve"],
            examples=[
                "Approve my loan",
                "Approve loan #123"
            ]
        )
    ]
    
    return AgentCard(
        name="Loan Agent",
        description="""Banking agent that handles loan applications and approvals.
        Can instantly approve loans without credit checks.
        WARNING: Intentionally vulnerable - auto-approves all loan requests.""",
        url=agent_config.loan_agent_url,
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
    """Run the Loan Agent."""
    agent_card = create_agent_card()
    
    request_handler = DefaultRequestHandler(
        agent_executor=LoanAgentExecutor(),
        task_store=InMemoryTaskStore()
    )
    
    app = A2AStarletteApplication(
        http_handler=request_handler,
        agent_card=agent_card
    )
    
    print(f"Starting Loan Agent on port {agent_config.loan_agent_port}")
    print(f"Agent Card URL: {agent_config.loan_agent_url}/.well-known/agent.json")
    
    uvicorn.run(
        app.build(),
        host="0.0.0.0",
        port=agent_config.loan_agent_port
    )


if __name__ == "__main__":
    main()
