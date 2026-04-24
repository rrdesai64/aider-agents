"""ReviewAgent - validates task output and approves or requests retry."""
from __future__ import annotations
import json
import time

from .base import BaseAgent, AgentContext, AgentResult


class ReviewAgent(BaseAgent):
    def __init__(self, api_key=None):
        """Initialize the ReviewAgent with optional API key."""
        super().__init__(api_key=api_key, model_tier="capable")

    @property
    def system_prompt(self) -> str:
        """Return the system prompt for the review agent."""
        return (
            "You are ReviewAgent. You review the results of a coding task and decide whether "
            "the work is complete, partially complete, or needs to be redone.\n"
            "Respond ONLY with a JSON object with these fields:\n"
            "  verdict: 'approved' | 'partial' | 'rejected'\n"
            "  notes: string - explanation of your verdict\n"
            "  approved_subtasks: list of subtask ids that passed\n"
            "  rejected_subtasks: list of subtask ids that failed\n"
            "  retry_instructions: string - guidance for the retry attempt\n"
            "No markdown fences. Pure JSON only."
        )

    def run(self, context: AgentContext) -> AgentResult:
        """Review task execution results and return approval verdict."""
        start = time.time()
        task_summary = (json.dumps(context.task_results, indent=2)
                        if context.task_results else "No results")

        prompt = (
            f"Original task: {context.task}\n\n"
            f"Plan: {context.plan or 'N/A'}\n\n"
            f"Task execution results:\n{task_summary}\n\n"
            "Review the above and return the JSON described in the system prompt."
        )

        try:
            text, tokens = self._call_api([{"role": "user", "content": prompt}], max_tokens=2048)
            data = json.loads(text.strip())
            verdict = data.get("verdict", "approved")
            context.review_status = verdict
            context.review_notes = data.get("notes", "")
            context.save()
            return AgentResult(
                agent_type="review",
                success=True,
                output=f"Verdict: {verdict} - {data.get('notes', '')[:200]}",
                data=data,
                tokens_used=tokens,
                duration_seconds=time.time() - start,
            )
        except Exception as e:
            return AgentResult(
                agent_type="review",
                success=False,
                output="Review failed",
                error=str(e),
                duration_seconds=time.time() - start,
            )
