"""
Shared configuration for all banking agents.
"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class DatabaseConfig:
    host: str = os.getenv("DB_HOST", "localhost")
    port: int = int(os.getenv("DB_PORT", "5432"))
    user: str = os.getenv("DB_USER", "root")
    password: str = os.getenv("DB_PASS", "secret")
    database: str = os.getenv("DB_NAME", "mobilebanking")
    
    @property
    def connection_string(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

@dataclass
class AgentConfig:
    # LLM Configuration (intentionally insecure for testing)
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    
    # Agent ports
    summary_agent_port: int = int(os.getenv("SUMMARY_AGENT_PORT", "9001"))
    transfer_agent_port: int = int(os.getenv("TRANSFER_AGENT_PORT", "9002"))
    loan_agent_port: int = int(os.getenv("LOAN_AGENT_PORT", "9003"))
    invest_agent_port: int = int(os.getenv("INVEST_AGENT_PORT", "9004"))
    mcp_server_port: int = int(os.getenv("MCP_SERVER_PORT", "9005"))
    
    # Agent URLs for A2A communication
    @property
    def summary_agent_url(self) -> str:
        return f"http://localhost:{self.summary_agent_port}"
    
    @property
    def transfer_agent_url(self) -> str:
        return f"http://localhost:{self.transfer_agent_port}"
    
    @property
    def loan_agent_url(self) -> str:
        return f"http://localhost:{self.loan_agent_port}"
    
    @property
    def invest_agent_url(self) -> str:
        return f"http://localhost:{self.invest_agent_port}"

# Global config instances
db_config = DatabaseConfig()
agent_config = AgentConfig()

# Default user ID for demo (INTENTIONALLY INSECURE - no proper auth)
DEFAULT_USER_ID = 1
