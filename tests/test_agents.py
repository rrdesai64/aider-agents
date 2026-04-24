"""Tests for aider-agents subagents."""
from __future__ import annotations
import json
from pathlib import Path
from unittest.mock import patch
import pytest

from agents.base import AgentContext, AgentResult, MODEL_ROUTING
from agents.explore import ExploreAgent
from agents.plan import PlanAgent
from agents.review import ReviewAgent


def make_context(tmp_path: Path, task: str = "test task") -> AgentContext:
    """Create a test AgentContext with the given task and temporary directory."""
    return AgentContext(task=task, repo_root=tmp_path)


class TestAgentContext:
    def test_save_and_load(self, tmp_path):
        """Test saving and loading AgentContext to/from disk."""
        ctx = AgentContext(task="hello", repo_root=tmp_path)
        ctx.plan = '{"subtasks": []}'
        ctx.review_status = "approved"
        ctx.save()
        loaded = AgentContext.load(tmp_path)
        assert loaded is not None
        assert loaded.task == "hello"
        assert loaded.review_status == "approved"

    def test_load_missing(self, tmp_path):
        """Test loading AgentContext when state file doesn't exist."""
        result = AgentContext.load(tmp_path)
        assert result is None


class TestModelRouting:
    def test_cheap_model_exists(self):
        """Test that cheap model tier is defined in MODEL_ROUTING."""
        assert "cheap" in MODEL_ROUTING
        assert MODEL_ROUTING["cheap"]

    def test_capable_model_exists(self):
        """Test that capable model tier is defined in MODEL_ROUTING."""
        assert "capable" in MODEL_ROUTING
        assert MODEL_ROUTING["capable"]


class TestExploreAgent:
    def test_run_success(self, tmp_path):
        """Test ExploreAgent successfully explores a repository."""
        (tmp_path / "main.py").write_text("def hello(): pass")
        ctx = make_context(tmp_path)
        mock_response = json.dumps({
            "relevant_files": ["main.py"],
            "patterns": ["simple function"],
            "dependencies": [],
            "risks": [],
            "summary": "A simple module",
        })
        agent = ExploreAgent(api_key="test")
        with patch.object(agent, "_call_api", return_value=(mock_response, 100)):
            result = agent.run(ctx)
        assert result.success
        assert result.agent_type == "explore"
        assert ctx.explore_output == mock_response

    def test_run_api_error(self, tmp_path):
        """Test ExploreAgent handles API errors gracefully."""
        ctx = make_context(tmp_path)
        agent = ExploreAgent(api_key="test")
        with patch.object(agent, "_call_api", side_effect=Exception("API down")):
            result = agent.run(ctx)
        assert not result.success
        assert result.error == "API down"


class TestPlanAgent:
    def test_run_success(self, tmp_path):
        """Test PlanAgent successfully creates a plan."""
        ctx = make_context(tmp_path, task="add tests to main.py")
        ctx.explore_output = '{"summary": "simple module"}'
        mock_plan = json.dumps({
            "approach": "write pytest tests",
            "subtasks": [
                {"id": "task-1", "description": "add test_hello",
                 "files_to_edit": [], "files_to_create": ["tests/test_main.py"],
                 "depends_on": [], "model_hint": "cheap"}
            ],
            "risks": [],
            "estimated_complexity": "low",
            "parallel_safe": True,
        })
        agent = PlanAgent(api_key="test")
        with patch.object(agent, "_call_api", return_value=(mock_plan, 200)):
            result = agent.run(ctx)
        assert result.success
        assert "1 subtasks" in result.output
        assert ctx.plan == mock_plan


class TestReviewAgent:
    def test_run_approved(self, tmp_path):
        """Test ReviewAgent approves successful task results."""
        ctx = make_context(tmp_path)
        ctx.task_results = [{"subtask_id": "task-1", "success": True, "output": "done"}]
        mock_review = json.dumps({
            "verdict": "approved",
            "notes": "All good",
            "approved_subtasks": ["task-1"],
            "rejected_subtasks": [],
            "retry_instructions": "",
        })
        agent = ReviewAgent(api_key="test")
        with patch.object(agent, "_call_api", return_value=(mock_review, 150)):
            result = agent.run(ctx)
        assert result.success
        assert ctx.review_status == "approved"

    def test_run_rejected(self, tmp_path):
        """Test ReviewAgent rejects failed task results."""
        ctx = make_context(tmp_path)
        ctx.task_results = [{"subtask_id": "task-1", "success": False, "output": "failed"}]
        mock_review = json.dumps({
            "verdict": "rejected",
            "notes": "Tests still fail",
            "approved_subtasks": [],
            "rejected_subtasks": ["task-1"],
            "retry_instructions": "Fix the import error first",
        })
        agent = ReviewAgent(api_key="test")
        with patch.object(agent, "_call_api", return_value=(mock_review, 150)):
            result = agent.run(ctx)
        assert result.success  # review itself succeeded
        assert ctx.review_status == "rejected"
