"""PlanAgent - designs step-by-step subtask list."""
from __future__ import annotations
import json
import time

from .base import BaseAgent, AgentContext, AgentResult


class PlanAgent(BaseAgent):
    def __init__(self, api_key=None):
        """Initialize the PlanAgent with optional API key."""
        super().__init__(api_key=api_key, model_tier="capable")

    @property
    def system_prompt(self) -> str:
        """Return the system prompt for the PlanAgent."""
        return (
            "You are PlanAgent. You design a precise, atomic subtask list for a coding task. "
            "Respond ONLY with a JSON object with these fields:\n"
            "  approach: string - overall strategy\n"
            "  subtasks: list of objects, each with:\n"
            "    id: string like 'task-1'\n"
            "    description: string - what to do\n"
            "    files_to_edit: list of file paths\n"
            "    files_to_create: list of file paths\n"
            "    depends_on: list of task ids\n"
            "    model_hint: 'cheap' or 'capable'\n"
            "  risks: list of strings\n"
            "  estimated_complexity: 'low' | 'medium' | 'high'\n"
            "  parallel_safe: boolean\n"
            "No markdown fences. Pure JSON only."
        )

    def run(self, context: AgentContext) -> AgentResult:
        """Execute the planning phase and generate a subtask plan."""
        start = time.time()
        explore_section = ""
        if context.explore_output:
            explore_section = f"\nExplore results:\n{context.explore_output}\n"

        prompt = (
            f"Task: {context.task}\n"
            f"Repository map:\n{context.repo_map}\n"
            f"{explore_section}\n"
            "Design a step-by-step subtask plan and return the JSON described in the system prompt."
        )

        try:
            text, tokens = self._call_api([{"role": "user", "content": prompt}], max_tokens=4096)
            data = json.loads(text.strip())
            context.plan = text
            context.save()
            subtask_count = len(data.get("subtasks", []))
            return AgentResult(
                agent_type="plan",
                success=True,
                output=f"Plan created: {subtask_count} subtasks, complexity={data.get('estimated_complexity')}",
                data=data,
                tokens_used=tokens,
                duration_seconds=time.time() - start,
            )
        except Exception as e:
            return AgentResult(
                agent_type="plan",
                success=False,
                output="Planning failed",
                error=str(e),
                duration_seconds=time.time() - start,
            )
