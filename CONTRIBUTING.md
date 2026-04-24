# Contributing to aider-agents

## Architecture

```
BaseAgent (agents/base.py)
    +-- ExploreAgent   - read-only, cheap model
    +-- PlanAgent      - read-only, capable model
    +-- TaskAgent      - file-editing, spawns headless Aider
    +-- ReviewAgent    - read-only, capable model
    +-- WebSearchAgent - Tavily search + Claude synthesis

AgentPool (orchestrator.py)
    - runs Explore -> WebSearch -> Plan -> Task -> Review

mcp_server.py
    - exposes AgentPool as MCP tools for Aider
```

Core rule: only TaskAgent touches the filesystem.

## Dev setup

```bash
git clone https://github.com/rrdesai64/aider-agents
cd aider-agents
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -e ".[dev]"
set ANTHROPIC_API_KEY=sk-ant-...
pytest tests/ -v
```

## Adding a new agent

1. Create agents/your_agent.py subclassing BaseAgent
2. Implement system_prompt property and run() method
3. Register in agents/__init__.py
4. Add to MODEL_ROUTING in agents/base.py
5. Wire into orchestrator.py if needed
6. Expose as MCP tool in mcp_server.py
7. Write tests in tests/test_agents.py

## PR checklist

- Tests pass: pytest tests/ -v
- No real API keys in code or tests
- New agent follows BaseAgent pattern
- MCP tool added if callable from Aider
- Entry in README agent table

## License

MIT
