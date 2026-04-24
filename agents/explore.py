"""ExploreAgent - reads repo and extracts relevant context."""
from __future__ import annotations
import json
import time
from pathlib import Path

from .base import BaseAgent, AgentContext, AgentResult


class ExploreAgent(BaseAgent):
    def __init__(self, api_key=None):
        super().__init__(api_key=api_key, model_tier="cheap")

    @property
    def system_prompt(self) -> str:
        return (
            "You are ExploreAgent. You analyse a code repository and extract relevant context "
            "for a given task. Respond ONLY with a JSON object with these fields:\n"
            "  relevant_files: list of file paths relevant to the task\n"
            "  patterns: list of patterns or conventions observed\n"
            "  dependencies: list of key dependencies relevant to the task\n"
            "  risks: list of risk factors or things to be careful about\n"
            "  summary: one-paragraph summary of what you found\n"
            "No markdown fences. Pure JSON only."
        )

    def run(self, context: AgentContext) -> AgentResult:
        start = time.time()
        if not context.repo_map:
            context.repo_map = self._build_repo_map(context.repo_root)

        file_snippets = self._sample_files(context.repo_root, context.repo_map)

        prompt = (
            f"Task: {context.task}\n\n"
            f"Repository file listing:\n{context.repo_map}\n\n"
            f"File snippets:\n{file_snippets}\n\n"
            "Analyse the repository and return the JSON described in the system prompt."
        )

        try:
            text, tokens = self._call_api([{"role": "user", "content": prompt}], max_tokens=2048)
            data = json.loads(text.strip())
            context.explore_output = text
            context.save()
            return AgentResult(
                agent_type="explore",
                success=True,
                output=data.get("summary", "Explore complete"),
                data=data,
                tokens_used=tokens,
                duration_seconds=time.time() - start,
            )
        except Exception as e:
            return AgentResult(
                agent_type="explore",
                success=False,
                output="Explore failed",
                error=str(e),
                duration_seconds=time.time() - start,
            )

    def _sample_files(self, repo_root: Path, repo_map: str, max_files: int = 15) -> str:
        skip_ext = {".pyc", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
                    ".pdf", ".zip", ".tar", ".gz", ".lock"}
        snippets = []
        count = 0
        for line in repo_map.splitlines():
            if count >= max_files:
                break
            p = repo_root / line.strip()
            if p.is_file() and p.suffix not in skip_ext:
                try:
                    content = p.read_text(encoding="utf-8", errors="ignore")
                    lines = content.splitlines()[:80]
                    snippets.append(f"=== {line.strip()} ===\n" + "\n".join(lines))
                    count += 1
                except Exception:
                    pass
        return "\n\n".join(snippets)
