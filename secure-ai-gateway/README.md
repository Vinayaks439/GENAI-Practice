# Secure AI Agent Gateway with Compliance Controls

A comprehensive project demonstrating **AI/ML Security, A2A Protocol, MCP, Google ADK, and LangChain** with enterprise-grade security controls.

## 🎯 Project Purpose

This project is designed to practice and demonstrate skills for an **AI/ML Security Specialist** role:

- ✅ **A2A (Agent-to-Agent Protocol)** - Inter-agent communication with security scanning
- ✅ **MCP (Model Context Protocol)** - Tool integration with security controls
- ✅ **Google ADK** - Agent Development Kit integration
- ✅ **LangChain** - LLM orchestration with guardrails
- ✅ **Security Controls** - OWASP, input validation, rate limiting
- ✅ **Compliance** - ISO27001, SOC2, NIST logging and controls
- ✅ **Security Testing** - PromptFoo, Garak, PyRIT integration hooks

## 📁 Project Structure

```
secure-ai-gateway/
├── mcp_server/              # MCP Server with security tools
│   ├── server.py            # Main MCP server
│   ├── tools/               # Security-focused tools
│   │   ├── prompt_analyzer.py
│   │   ├── pii_detector.py
│   │   └── compliance_checker.py
│   └── config.py
│
├── a2a_agents/              # A2A Protocol implementation
│   ├── security_agent/      # Security scanning agent
│   │   ├── agent.py
│   │   ├── agent_executor.py
│   │   └── skills/
│   ├── compliance_agent/    # Audit & compliance agent
│   │   ├── agent.py
│   │   └── skills/
│   └── orchestrator/        # Agent orchestration
│       └── coordinator.py
│
├── langchain_agents/        # LangChain with security guardrails
│   ├── secure_agent.py
│   ├── guardrails/
│   │   ├── input_validator.py
│   │   ├── output_filter.py
│   │   └── prompt_injection_detector.py
│   └── chains/
│       └── secure_chain.py
│
├── security/                # Core security controls
│   ├── owasp_controls.py    # OWASP Top 10 for LLM controls
│   ├── input_sanitizer.py
│   ├── rate_limiter.py
│   ├── audit_logger.py
│   └── secrets_manager.py
│
├── compliance/              # Compliance & audit modules
│   ├── iso27001.py          # ISO 27001 controls
│   ├── soc2.py              # SOC 2 controls
│   ├── nist_ai_rmf.py       # NIST AI Risk Management Framework
│   └── audit_evidence.py    # Evidence collection for audits
│
├── testing/                 # Security testing integration
│   ├── promptfoo_config.yaml
│   ├── garak_tests/
│   ├── pyrit_scenarios/
│   └── security_test_runner.py
│
├── adk_agents/              # Google Agent Development Kit
│   ├── security_analyst.py
│   └── tools/
│
├── requirements.txt
├── .env.example
└── docker-compose.yaml
```

## 🚀 Quick Start

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy environment file
cp .env.example .env
# Edit .env with your API keys

# 4. Run the MCP server
python -m mcp_server.server

# 5. Run the A2A security agent
python -m a2a_agents.security_agent.agent

# 6. Run security tests
python -m testing.security_test_runner
```

## 📚 Learning Path

### Week 1: Foundations
- [ ] Set up the project and understand the structure
- [ ] Implement basic MCP server with one tool
- [ ] Create your first A2A agent

### Week 2: Security Controls
- [ ] Implement OWASP Top 10 for LLM controls
- [ ] Add input validation and sanitization
- [ ] Create audit logging system

### Week 3: Compliance
- [ ] Implement ISO27001 control logging
- [ ] Add SOC2 compliance checks
- [ ] Create audit evidence collection

### Week 4: Advanced Features
- [ ] Add PromptFoo security tests
- [ ] Integrate Garak for adversarial testing
- [ ] Set up PyRIT red-teaming scenarios

## 🔐 Security Controls Implemented

### OWASP Top 10 for LLM Applications
1. **LLM01: Prompt Injection** - Input validation & detection
2. **LLM02: Insecure Output Handling** - Output sanitization
3. **LLM03: Training Data Poisoning** - Data validation hooks
4. **LLM06: Sensitive Information Disclosure** - PII detection
5. **LLM07: Insecure Plugin Design** - Tool validation
6. **LLM08: Excessive Agency** - Action approval workflow
7. **LLM09: Overreliance** - Confidence scoring
8. **LLM10: Model Theft** - Access controls

### Compliance Standards
- **ISO 27001**: Information security controls
- **SOC 2**: Trust service criteria
- **NIST AI RMF**: AI risk management framework

## 🛠️ Key Technologies

| Technology | Purpose |
|------------|---------|
| A2A Protocol | Agent-to-agent communication |
| MCP | Model Context Protocol for tools |
| Google ADK | Agent Development Kit |
| LangChain | LLM orchestration |
| PromptFoo | Prompt security testing |
| Garak | LLM vulnerability scanning |
| PyRIT | Red teaming framework |

## 📖 Documentation

- [MCP Server Guide](docs/mcp_server.md)
- [A2A Protocol Implementation](docs/a2a_agents.md)
- [Security Controls Reference](docs/security_controls.md)
- [Compliance Guide](docs/compliance.md)
- [Testing Guide](docs/testing.md)

## License

MIT License - See LICENSE file
