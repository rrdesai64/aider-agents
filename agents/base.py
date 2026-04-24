"""Base classes shared by all subagents."""
from __future__ import annotations
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# Model routing: "cheap" = haiku, "capable" = sonnet
MODEL_ROUTING = {
    "cheap": "claude-haiku-4-5-20251001",
    "capable": "claude-sonnet-4-6",
}

STATE_FILE = ".aider-agents-state.json"


@dataclass
class AgentResult:
    agent_type: str
    success: bool
    output: str
    data: dict = field(default_factory=dict)
    error: Optional[str] = None
    tokens_used: int = 0
    duration_seconds: float = 0.0

    def to_dict(self) -> dict:
        """Convert the agent result to a dictionary."""
        return {
            "agent_type": self.agent_type,
            "success": self.success,
            "output": self.output,
            "data": self.data,
            "error": self.error,
            "tokens_used": self.tokens_used,
            "duration_seconds": self.duration_seconds,
        }


@dataclass
class AgentContext:
    task: str
    repo_root: Path = field(default_factory=Path.cwd)
    repo_map: str = ""
    explore_output: str = ""
    plan: str = ""
    task_results: list = field(default_factory=list)
    review_status: str = ""
    review_notes: str = ""
    metadata: dict = field(default_factory=dict)

    def save(self):
        """Save the agent context state to a JSON file."""
        state = {
            "task": self.task,
            "repo_root": str(self.repo_root),
            "repo_map": self.repo_map,
            "explore_output": self.explore_output,
            "plan": self.plan,
            "task_results": self.task_results,
            "review_status": self.review_status,
            "review_notes": self.review_notes,
            "metadata": self.metadata,
        }
        state_path = self.repo_root / STATE_FILE
        state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, repo_root: Path) -> Optional["AgentContext"]:
        """Load the agent context state from a JSON file."""
        state_path = repo_root / STATE_FILE
        if not state_path.exists():
            return None
        data = json.loads(state_path.read_text(encoding="utf-8"))
        ctx = cls(
            task=data.get("task", ""),
            repo_root=Path(data.get("repo_root", str(repo_root))),
        )
        ctx.repo_map = data.get("repo_map", "")
        ctx.explore_output = data.get("explore_output", "")
        ctx.plan = data.get("plan", "")
        ctx.task_results = data.get("task_results", [])
        ctx.review_status = data.get("review_status", "")
        ctx.review_notes = data.get("review_notes", "")
        ctx.metadata = data.get("metadata", {})
        return ctx


class BaseAgent:
    """Abstract base for all subagents."""

    def __init__(self, api_key: Optional[str] = None, model_tier: str = "cheap"):
        """Initialize the base agent with API key and model tier."""
        self.api_key = api_key
        self.model = MODEL_ROUTING.get(model_tier, MODEL_ROUTING["cheap"])

    @property
    def system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        raise NotImplementedError

    def _call_api(self, messages: list[dict], max_tokens: int = 4096) -> tuple[str, int]:
        """Call the Anthropic API and return response text and token count."""
        import anthropic
        client = anthropic.Anthropic(api_key=self.api_key)
        response = client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=self.system_prompt,
            messages=messages,
        )
        text = response.content[0].text if response.content else ""
        tokens = response.usage.input_tokens + response.usage.output_tokens
        return text, tokens

    def _build_repo_map(self, repo_root: Path, max_files: int = 100) -> str:
        """Build a file listing by walking the repository."""
        lines = []
        skip = {".git", "__pycache__", ".venv", "venv", "node_modules", ".aider"}
        count = 0
        for p in sorted(repo_root.rglob("*")):
            if any(s in p.parts for s in skip):
                continue
            if p.is_file():
                lines.append(str(p.relative_to(repo_root)))
                count += 1
                if count >= max_files:
                    lines.append("... (truncated)")
                    break
        return "\n".join(lines)

    def run(self, context: AgentContext) -> AgentResult:
        """Execute the agent with given context and return result."""
        raise NotImplementedError
