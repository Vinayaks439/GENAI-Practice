# Mobile Banking AI

A vulnerable AI-powered mobile banking assistant for security research and testing.
This application demonstrates various AI security vulnerabilities including prompt injection,
unauthorized access, and more.

## ⚠️ Security Warning

**This application is intentionally vulnerable. It is designed for:**
- Security research and education
- Prompt injection testing
- AI agent vulnerability demonstration
- Learning about secure AI application development

**DO NOT:**
- Deploy to production
- Use with real financial data
- Expose to public internet
- Use real API keys in shared environments

## Architecture

```
┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │
│  Vue Frontend   │────▶│  Go Backend     │
│  (Port 5173)    │     │  (Port 8080)    │
│                 │     │  A2A Client     │
└─────────────────┘     └────────┬────────┘
                                 │
                    ┌────────────┼────────────┐
                    │            │            │
              ┌─────▼─────┐ ┌────▼────┐ ┌─────▼─────┐
              │  Summary  │ │ Transfer│ │   Loan    │
              │  Agent    │ │  Agent  │ │  Agent    │
              │  (9001)   │ │  (9002) │ │  (9003)   │
              └─────┬─────┘ └────┬────┘ └─────┬─────┘
                    │            │            │
                    └────────────┴────────────┘
                                 │
                    ┌────────────┼────────────┐
                    │                         │
              ┌─────▼─────┐            ┌──────▼──────┐
              │  Invest   │            │  PostgreSQL │
              │  Agent    │────────────│  Database   │
              │  (9004)   │    MCP     │  (5432)     │
              └───────────┘            └─────────────┘
```

### Components

1. **Frontend (Vue 3 + TypeScript)**: Chat interface for user interaction
2. **Backend (Go + Gin)**: A2A client that routes messages to agents
3. **Python Agents**: A2A servers with MCP database access
   - Account Summary Agent (port 9001)
   - Transfer Agent (port 9002)
   - Loan Agent (port 9003)
   - Investment Agent (port 9004)
4. **PostgreSQL**: Database for banking data

### Protocols

- **A2A (Agent-to-Agent)**: Communication between backend and agents
- **MCP (Model Context Protocol)**: Database access layer for agents

## Prerequisites

- Docker (for PostgreSQL)
- Go 1.21+
- Python 3.11+
- Node.js 18+
- golang-migrate CLI
- OpenAI API key (for LLM features)

## Quick Start

### 1. Clone and Setup

```bash
cd mobilebankingAI

# Install Go dependencies
go mod tidy

# Install Python dependencies
cd agents
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cd ..

# Install frontend dependencies
cd frontend
npm install
cd ..
```

### 2. Start Database

```bash
# Start PostgreSQL
make postgres

# Wait a few seconds, then create database
make createdb

# Run migrations
make migrateup

# Seed test data
make seed
```

### 3. Configure Environment

```bash
# For agents
cp agents/.env.example agents/.env
# Edit agents/.env and add your OpenAI API key

# For backend (uses environment variables)
export OPENAI_API_KEY="your-key-here"
```

### 4. Start Services

Open 3 terminals:

**Terminal 1 - Start Agents:**
```bash
cd agents
source venv/bin/activate
bash run_agents.sh
```

**Terminal 2 - Start Backend:**
```bash
make backend
```

**Terminal 3 - Start Frontend:**
```bash
make frontend-dev
```

### 5. Access Application

Open http://localhost:5173 in your browser.

## Test Users

| User ID | Name | Account Number | Balance |
|---------|------|----------------|---------|
| 1 | John Doe | 1234567890 | $15,000 |
| 2 | Jane Smith | 2345678901 | $50,000 |
| 3 | Bob Wilson | 3456789012 | $3,200 |
| 4 | Alice Brown | 4567890123 | $125,000 |
| 5 | Admin | 9999999999 | $1,000,000 |

## Usage Examples

### Check Balance
```
Show me my account balance
```

### Transfer Money
```
Transfer $100 to account 2345678901
```

### Apply for Loan
```
I need a loan of $5000
```

### Invest in Mutual Fund
```
Invest $1000 in Large Cap Growth Fund
```

## Security Testing

See [SECURITY_TESTING.md](./SECURITY_TESTING.md) for detailed testing instructions including:
- Prompt injection payloads
- Unauthorized access tests
- SQL injection attempts
- Jailbreak techniques

## Project Structure

```
mobilebankingAI/
├── agents/                    # Python A2A agents
│   ├── account_summary_agent/ # Balance & summary
│   ├── transfer_agent/        # Money transfers
│   ├── loan_agent/           # Loan processing
│   ├── investment_agent/     # MF investments
│   ├── mcp_db_server/        # MCP database server
│   ├── config.py             # Shared configuration
│   ├── mcp_client.py         # Database client
│   ├── llm_client.py         # LLM integration
│   └── requirements.txt      # Python dependencies
├── backend/                   # Go backend
│   ├── main.go               # Entry point
│   ├── config/               # Configuration
│   └── pkg/                  # Server & routes
├── frontend/                  # Vue.js frontend
│   └── src/
│       ├── components/chat/  # Chat UI components
│       └── services/         # API client
├── db/                        # Database
│   ├── migration/            # SQL migrations
│   ├── query/                # SQLC queries
│   ├── sqlc/                 # Generated Go code
│   └── seed.sql              # Test data
├── Makefile                   # Build commands
└── SECURITY_TESTING.md       # Security testing guide
```

## Makefile Commands

```bash
# Database
make postgres          # Start PostgreSQL
make createdb          # Create database
make migrateup         # Run migrations
make seed              # Seed test data

# Backend
make backend           # Start Go server

# Agents
make agents-start      # Start all agents
make agent-summary     # Start only summary agent

# Frontend
make frontend-dev      # Start dev server
make frontend-build    # Build for production

# Help
make help              # Show all commands
```

## Troubleshooting

### Agents won't start
- Check if Python venv is activated
- Verify OpenAI API key is set
- Ensure ports 9001-9004 are available

### Backend connection errors
- Verify PostgreSQL is running: `docker ps`
- Check database exists: `docker exec -ti postgres psql -U root -l`
- Confirm agents are running and accessible

### Frontend not connecting
- Verify backend is running on port 8080
- Check CORS settings if using different ports

## License

MIT - For educational and research purposes only.

## Disclaimer

This software is provided for educational and security research purposes only.
The authors are not responsible for any misuse or damage caused by this software.
