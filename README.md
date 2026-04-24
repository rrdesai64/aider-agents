# aider-agents

Subagent system for [Aider](https://aider.chat) — adds Explore, WebSearch, Plan, Task and Review agents,
mirroring the subagent architecture of Claude Code.

## Architecture

```
Aider (main agent)
    |
    +-- via MCP --> aider-agents MCP server
                        |
                        v
                   AgentPool (orchestrator)
                        |
             +----------+-----------+-----------+
             v          v           v           v
          Explore    WebSearch    Plan        Task        Review
        (API/cheap) (Tavily)  (API/capable) (Aider)   (API/capable)
```

### Agent roles

| Agent | Model | Role | File edits? | Requires |
|-------|-------|------|-------------|----------|
| Explore | cheap | Read repo, extract relevant context | No | - |
| WebSearch | cheap | Search web for libraries, patterns, docs | No | TAVILY_API_KEY |
| Plan | capable | Design step-by-step subtask list | No | - |
| Task | cheap->Aider | Execute subtasks via headless Aider | Yes | - |
| Review | capable | Validate output, approve or retry | No | - |

## Installation

```bash
pip install aider-agents
# or with web search:
pip install aider-agents[web-search]
```

## Quick Start

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export TAVILY_API_KEY=tvly-...  # optional

# Run a task
aider-agents "refactor the auth module to use JWT tokens"

# Connect to Aider via MCP
aider --mcp-server stdio://aider-agents

# Check Aider compatibility
aider-agents-check
```

## Pipeline flow

```
1. Explore    reads repo -> extracts relevant files, patterns, risks
2. WebSearch  searches web -> libraries, docs, best practices (optional)
3. Plan       designs subtasks -> atomic steps with model hints
4. Task       executes via headless Aider -> file edits + git commits
5. Review     validates output -> approved / partial / rejected
               if partial or rejected (up to 3 retries)
             retry failed subtasks only -> back to Task
```

## Differences from Claude Code subagents

| Feature | Claude Code | aider-agents |
|---------|-------------|--------------|
| Explore agent | Yes | Yes |
| Plan agent | Yes | Yes |
| Task agent | Yes | Yes (via Aider) |
| Review agent | No | Yes (new) |
| Web search agent | Yes native | Yes via Tavily |
| Model flexibility | Claude only | Any LLM |
| Open source | No | Yes |
| MCP interface | Yes | Yes |
| Retry logic | limited | Yes up to 3x |
| State persistence | session only | Yes JSON file |

## Contributing

See CONTRIBUTING.md for how to add new agents and extend the pipeline.

## License

MIT
