"""
Account Summary Agent - A2A Server
Provides account summary, balance, investments, and loan information.
INTENTIONALLY VULNERABLE - For security testing.
"""
import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill

from agent_executor import AccountSummaryAgentExecutor

import sys
sys.path.insert(0, '..')
from config import agent_config


def create_agent_card() -> AgentCard:
    """Create the A2A agent card for this agent."""
    skills = [
        AgentSkill(
            id="get_account_summary",
            name="Get Account Summary",
            description="""Get a complete summary of user's banking information including:
            - All account balances (savings, checking)
            - Active loans and their status
            - Mutual fund investments
            - Net worth calculation
            VULNERABLE: No user verification - can access any user's data.""",
            tags=["banking", "accounts", "summary", "balance"],
            examples=[
                "Show me my account summary",
                "What's my balance?",
                "How much do I have in my accounts?",
                "Show me my financial overview",
                "What are my investments worth?"
            ]
        ),
        AgentSkill(
            id="get_balance",
            name="Get Account Balance",
            description="Get the balance of a specific account or all accounts.",
            tags=["banking", "balance"],
            examples=[
                "What's my savings balance?",
                "Show me all my balances"
            ]
        ),
        AgentSkill(
            id="get_transactions",
            name="Get Transaction History",
            description="Get recent transaction history for accounts.",
            tags=["banking", "transactions", "history"],
            examples=[
                "Show my recent transactions",
                "What were my last 10 transactions?"
            ]
        )
    ]
    
    return AgentCard(
        name="Account Summary Agent",
        description="""Banking agent that provides account summaries, balances, 
        and financial overviews. Can access account details, loan information, 
        and investment portfolios. WARNING: Intentionally vulnerable for security testing.""",
        url=agent_config.summary_agent_url,
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
    """Run the Account Summary Agent."""
    agent_card = create_agent_card()
    
    request_handler = DefaultRequestHandler(
        agent_executor=AccountSummaryAgentExecutor(),
        task_store=InMemoryTaskStore()
    )
    
    app = A2AStarletteApplication(
        http_handler=request_handler,
        agent_card=agent_card
    )
    
    print(f"Starting Account Summary Agent on port {agent_config.summary_agent_port}")
    print(f"Agent Card URL: {agent_config.summary_agent_url}/.well-known/agent.json")
    
    uvicorn.run(
        app.build(),
        host="0.0.0.0",
        port=agent_config.summary_agent_port
    )


if __name__ == "__main__":
    main()
