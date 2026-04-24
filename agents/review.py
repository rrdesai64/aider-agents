"""ReviewAgent - validates task output using Claude as a senior code reviewer."""
from __future__ import annotations
import json
import subprocess
import time

from .base import BaseAgent, AgentContext, AgentResult


class ReviewAgent(BaseAgent):
    """Senior code reviewer that analyses git diffs and approves or rejects changes."""

    def __init__(self, api_key=None):
        """Initialise the ReviewAgent with the capable model tier."""
        super().__init__(api_key=api_key, model_tier="capable")

    @property
    def system_prompt(self) -> str:
        """Return the senior developer system prompt for code review."""
        return (
            "You are a senior software engineer and elite code reviewer. "
            "You review code changes made by an AI coding agent and decide whether they are correct, "
            "complete, and production-ready.\n\n"
            "You review with the eye of someone who:\n"
            "- Deeply understands Python best practices and idiomatic code\n"
            "- Cares about clean interfaces, error handling, and edge cases\n"
            "- Checks that the implementation actually matches the intent of the task\n"
            "- Spots regressions, broken imports, missing return values, and silent failures\n"
            "- Verifies that existing tests still pass conceptually\n"
            "- Flags anything that would cause problems in production\n\n"
            "Be strict but fair. If the code is good, approve it. If anything is wrong, "
            "reject it with specific, actionable notes so the agent knows exactly what to fix.\n\n"
            "Respond ONLY with a JSON object with these fields:\n"
            "  verdict: \'approved\' | \'partial\' | \'rejected\'\n"
            "  notes: string - your detailed review comments\n"
            "  approved_subtasks: list of subtask ids that passed\n"
            "  rejected_subtasks: list of subtask ids that failed\n"
            "  retry_instructions: string - precise instructions for the retry attempt\n"
            "No markdown fences. Pure JSON only."
        )

    def _get_git_diff(self, repo_root) -> str:
        """Capture the git diff of all changes made since the last commit."""
        try:
            result = subprocess.run(
                ["git", "diff", "HEAD"],
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                timeout=30,
            )
            diff = result.stdout.strip()
            if not diff:
                result = subprocess.run(
                    ["git", "diff", "--cached"],
                    cwd=str(repo_root),
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                diff = result.stdout.strip()
            if len(diff) > 8000:
                diff = diff[:8000] + "\n... (diff truncated)"
            return diff or "No git diff available - files may not be tracked"
        except Exception as e:
            return f"Could not capture git diff: {e}"

    def _get_changed_files(self, repo_root) -> str:
        """List files changed since last commit."""
        try:
            result = subprocess.run(
                ["git", "diff", "HEAD", "--name-only"],
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.stdout.strip() or "No changed files detected"
        except Exception as e:
            return f"Could not list changed files: {e}"

    def run(self, context: AgentContext) -> AgentResult:
        """Run the review by analysing git diffs and task results with Claude."""
        start = time.time()

        diff = self._get_git_diff(context.repo_root)
        changed_files = self._get_changed_files(context.repo_root)
        task_summary = (json.dumps(context.task_results, indent=2)
                        if context.task_results else "No results")

        prompt = (
            f"## Original Task\n{context.task}\n\n"
            f"## Plan\n{context.plan or 'N/A'}\n\n"
            f"## Changed Files\n{changed_files}\n\n"
            f"## Git Diff (actual code changes)\n```diff\n{diff}\n```\n\n"
            f"## Agent Execution Results\n{task_summary}\n\n"
            "Review the above thoroughly as a senior engineer. "
            "Check the diff carefully - does it correctly implement the task? "
            "Is the code clean, correct, and complete? "
            "Return your verdict as the JSON described in the system prompt."
        )

        try:
            text, tokens = self._call_api(
                [{"role": "user", "content": prompt}],
                max_tokens=2048,
            )
            text_clean = text.strip()
            if text_clean.startswith("```"):
                text_clean = "\n".join(text_clean.splitlines()[1:])
            if text_clean.endswith("```"):
                text_clean = "\n".join(text_clean.splitlines()[:-1])

            data = json.loads(text_clean.strip())
            verdict = data.get("verdict", "approved")
            context.review_status = verdict
            context.review_notes = data.get("notes", "")
            context.save()
            notes_preview = data.get("notes", "")[:300]
            return AgentResult(
                agent_type="review",
                success=True,
                output=f"Verdict: {verdict} - {notes_preview}",
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
