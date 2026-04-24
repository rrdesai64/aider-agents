"""TaskAgent - executes subtasks via headless Aider."""
from __future__ import annotations
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from .base import BaseAgent, AgentContext, AgentResult


class TaskAgent(BaseAgent):
    def __init__(self, api_key: Optional[str] = None,
                 auto_commit: bool = True, dry_run: bool = False):
        super().__init__(api_key=api_key, model_tier="cheap")
        self.auto_commit = auto_commit
        self.dry_run = dry_run

    @property
    def system_prompt(self) -> str:
        return "You are TaskAgent. You execute coding subtasks precisely using Aider."

    def run(self, context: AgentContext) -> AgentResult:
        start = time.time()
        try:
            plan_data = json.loads(context.plan) if context.plan else {}
        except Exception:
            plan_data = {}

        subtasks = plan_data.get("subtasks", [])
        if not subtasks:
            subtasks = [{"id": "task-1", "description": context.task,
                         "files_to_edit": [], "files_to_create": []}]

        results = []
        all_success = True
        for subtask in subtasks:
            r = self._run_subtask(subtask, context)
            results.append(r)
            if not r["success"]:
                all_success = False

        context.task_results = results
        context.save()

        succeeded = sum(1 for r in results if r["success"])
        summary = f"{succeeded}/{len(results)} subtasks succeeded"
        return AgentResult(
            agent_type="task",
            success=all_success,
            output=summary,
            data={"subtask_results": results},
            duration_seconds=time.time() - start,
        )

    def _run_subtask(self, subtask: dict, context: AgentContext) -> dict:
        task_start = time.time()
        subtask_id = subtask.get("id", "task-?")
        description = subtask.get("description", "")
        files_to_edit = subtask.get("files_to_edit", [])
        files_to_create = subtask.get("files_to_create", [])

        if self.dry_run:
            return {"subtask_id": subtask_id, "success": True,
                    "output": f"[DRY RUN] Would execute: {description}",
                    "returncode": 0, "duration": 0.0}

        cmd = [sys.executable, "-m", "aider", "--yes", "--no-pretty"]
        if self.api_key:
            cmd += ["--anthropic-api-key", self.api_key]
        if not self.auto_commit:
            cmd += ["--no-auto-commits"]

        all_files = files_to_edit + files_to_create
        if all_files:
            cmd += all_files

        cmd += ["--message", description]

        try:
            proc = subprocess.run(
                cmd,
                cwd=str(context.repo_root),
                capture_output=True,
                text=True,
                timeout=300,
            )
            success = proc.returncode == 0
            output = proc.stdout[-2000:] if proc.stdout else proc.stderr[-2000:]
            return {
                "subtask_id": subtask_id,
                "success": success,
                "output": output,
                "returncode": proc.returncode,
                "duration": time.time() - task_start,
            }
        except subprocess.TimeoutExpired:
            return {"subtask_id": subtask_id, "success": False,
                    "output": "Aider timed out after 300s",
                    "returncode": -1, "duration": time.time() - task_start}
        except Exception as e:
            return {"subtask_id": subtask_id, "success": False,
                    "output": str(e), "returncode": -1,
                    "duration": time.time() - task_start}
