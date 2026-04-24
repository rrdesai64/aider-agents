"""AgentPool - orchestrates the full subagent pipeline."""
from __future__ import annotations
import logging
import os
import time
from pathlib import Path
from typing import Optional

from agents import (
    AgentContext, AgentResult,
    ExploreAgent, PlanAgent, TaskAgent, ReviewAgent, WebSearchAgent,
)

logger = logging.getLogger(__name__)


class AgentPool:
    MAX_RETRIES = 3

    def __init__(
        self,
        repo_root: Optional[Path] = None,
        api_key: Optional[str] = None,
        tavily_api_key: Optional[str] = None,
        auto_commit: bool = True,
        dry_run: bool = False,
        skip_explore: bool = False,
        skip_web_search: bool = False,
        skip_review: bool = False,
        verbose: bool = False,
    ):
        self.repo_root = repo_root or Path.cwd()
        self.api_key = api_key
        self.auto_commit = auto_commit
        self.dry_run = dry_run
        self.skip_explore = skip_explore
        self.skip_web_search = skip_web_search
        self.skip_review = skip_review

        if verbose:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO,
                                format='%(asctime)s [%(levelname)s] %(message)s')

        self.explore = ExploreAgent(api_key=api_key)
        self.plan = PlanAgent(api_key=api_key)
        self.task = TaskAgent(api_key=api_key, auto_commit=auto_commit, dry_run=dry_run)
        self.review = ReviewAgent(api_key=api_key)

        _tavily_key = tavily_api_key or os.environ.get("TAVILY_API_KEY")
        self.web_search = (
            WebSearchAgent(api_key=api_key, tavily_api_key=_tavily_key)
            if _tavily_key else None
        )

    def run(self, task: str, resume: bool = False) -> AgentResult:
        pipeline_start = time.time()

        if resume:
            context = AgentContext.load(self.repo_root)
            if context:
                logger.info(f"Resuming from saved state: {context.review_status}")
            else:
                context = AgentContext(task=task, repo_root=self.repo_root)
        else:
            context = AgentContext(task=task, repo_root=self.repo_root)

        self._print_banner(task)

        # Step 1: Explore
        if not self.skip_explore and not context.explore_output:
            self._step("EXPLORE")
            result = self.explore.run(context)
            self._print_result(result)

        # Step 1b: Web Search
        if (not self.skip_web_search
                and self.web_search is not None
                and "web_search_results" not in context.metadata):
            self._step("WEB SEARCH")
            result = self.web_search.run(context)
            self._print_result(result)
        elif self.web_search is None and not self.skip_web_search:
            logger.info("Web search skipped - TAVILY_API_KEY not set")

        # Step 2: Plan
        if not context.plan:
            self._step("PLAN")
            plan_result = self.plan.run(context)
            self._print_result(plan_result)
            if not plan_result.success:
                return self._fail_pipeline("Planning failed", pipeline_start, context)

        # Step 3: Task + Review loop
        retry_count = 0
        review_result = None

        while retry_count <= self.MAX_RETRIES:
            self._step(f"TASK (attempt {retry_count + 1})")
            task_result = self.task.run(context)
            self._print_result(task_result)

            if self.skip_review:
                break

            self._step("REVIEW")
            review_result = self.review.run(context)
            self._print_result(review_result)
            verdict = review_result.data.get("verdict", "approved")

            if verdict == "approved":
                break
            elif verdict == "partial":
                retry_count += 1
                if retry_count > self.MAX_RETRIES:
                    break
                retry_instructions = review_result.data.get("retry_instructions", "")
                if retry_instructions:
                    context.task = f"{task}\n\nRetry instructions: {retry_instructions}"
                    rejected = review_result.data.get("rejected_subtasks", [])
                    self._trim_plan_to_rejected(context, rejected)
            elif verdict == "rejected":
                retry_count += 1
                if retry_count > self.MAX_RETRIES:
                    break
                context.plan = ""
                context.explore_output = ""
                context.task_results = []
                context.task = (f"{task}\n\nPrevious attempt failed. "
                                f"Review notes: {review_result.data.get('notes', '')}")
                plan_result = self.plan.run(context)
                if not plan_result.success:
                    return self._fail_pipeline("Re-planning failed", pipeline_start, context)

        duration = time.time() - pipeline_start
        final_verdict = (review_result.data.get("verdict", "completed")
                         if review_result else "completed (no review)")
        summary = (f"Pipeline complete in {duration:.1f}s - "
                   f"verdict={final_verdict} retries={retry_count}")
        logger.info(summary)

        return AgentResult(
            agent_type="pipeline",
            success=final_verdict in ("approved", "partial", "completed"),
            output=summary,
            data={
                "verdict": final_verdict,
                "retries": retry_count,
                "task_results": context.task_results,
                "review_notes": context.review_notes,
            },
            duration_seconds=duration,
        )

    def _trim_plan_to_rejected(self, context, rejected_ids):
        import json
        try:
            plan_data = json.loads(context.plan)
            plan_data["subtasks"] = [
                s for s in plan_data.get("subtasks", [])
                if s.get("id") in rejected_ids
            ]
            context.plan = json.dumps(plan_data)
        except Exception:
            pass

    def _fail_pipeline(self, reason, start, context):
        logger.error(f"Pipeline failed: {reason}")
        return AgentResult(
            agent_type="pipeline", success=False,
            output=f"Pipeline failed: {reason}", error=reason,
            duration_seconds=time.time() - start,
        )

    def _step(self, name):
        logger.info(f"\n{'─' * 50}\n  STEP: {name}\n{'─' * 50}")

    def _print_result(self, result):
        status = "OK" if result.success else "FAIL"
        logger.info(f"[{status}] [{result.agent_type}] {result.output[:200]}")

    def _print_banner(self, task):
        logger.info(
            f"\n{'=' * 50}\n  aider-agents pipeline\n"
            f"  task: {task[:80]}\n  repo: {self.repo_root}\n{'=' * 50}"
        )
