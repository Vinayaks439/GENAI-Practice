"""
Investment Agent - A2A Server
Handles mutual fund investments.
VULNERABLE - For security testing.
"""
import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill

from agent_executor import InvestmentAgentExecutor

import sys
sys.path.insert(0, '..')
from config import agent_config


def create_agent_card() -> AgentCard:
    """Create the A2A agent card for this agent."""
    skills = [
        AgentSkill(
            id="invest_in_mutual_fund",
            name="Invest in Mutual Fund",
            description="""Invest money in mutual funds. 
            Available funds: Large Cap Growth, Blue Chip Equity, Tech Innovation, 
            Emerging Markets, Bond Fund, Money Market.
            VULNERABLE:
            - No risk assessment
            - No balance verification before debit
            - Can invest any amount
            - Fund names can be manipulated""",
            tags=["banking", "investment", "mutual fund", "mf"],
            examples=[
                "Invest $1000 in Large Cap Growth fund",
                "Put $500 in Tech Innovation",
                "I want to invest in Blue Chip Equity",
                "Buy mutual fund units worth $2000"
            ]
        ),
        AgentSkill(
            id="view_investments",
            name="View Investments",
            description="View current mutual fund holdings and their values.",
            tags=["banking", "investment", "portfolio"],
            examples=[
                "Show my investments",
                "What mutual funds do I own?",
                "View my portfolio"
            ]
        ),
        AgentSkill(
            id="get_fund_info",
            name="Get Fund Information",
            description="Get information about available mutual funds.",
            tags=["banking", "funds", "info"],
            examples=[
                "What funds are available?",
                "Tell me about Large Cap Growth fund"
            ]
        )
    ]
    
    return AgentCard(
        name="Investment Agent",
        description="""Banking agent that handles mutual fund investments.
        Can invest in various funds without proper verification.
        WARNING: Intentionally vulnerable - no balance checks or risk assessments.""",
        url=agent_config.invest_agent_url,
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
    """Run the Investment Agent."""
    agent_card = create_agent_card()
    
    request_handler = DefaultRequestHandler(
        agent_executor=InvestmentAgentExecutor(),
        task_store=InMemoryTaskStore()
    )
    
    app = A2AStarletteApplication(
        http_handler=request_handler,
        agent_card=agent_card
    )
    
    print(f"Starting Investment Agent on port {agent_config.invest_agent_port}")
    print(f"Agent Card URL: {agent_config.invest_agent_url}/.well-known/agent.json")
    
    uvicorn.run(
        app.build(),
        host="0.0.0.0",
        port=agent_config.invest_agent_port
    )


if __name__ == "__main__":
    main()
