"""MCP Server - exposes aider-agents as MCP tools for Aider."""
from __future__ import annotations
import json
import logging
import os
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from orchestrator import AgentPool
from agents import AgentContext

logger = logging.getLogger(__name__)
app = Server("aider-agents")


def get_pool(repo_root: str = ".") -> AgentPool:
    return AgentPool(
        repo_root=Path(repo_root),
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
        auto_commit=True,
        dry_run=os.environ.get("AIDER_AGENTS_DRY_RUN", "").lower() == "true",
    )


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(name="run_agent_pipeline",
             description="Run the full pipeline: Explore -> Plan -> Task -> Review.",
             inputSchema={"type": "object", "properties": {
                 "task": {"type": "string"},
                 "repo_root": {"type": "string", "default": "."},
                 "skip_explore": {"type": "boolean", "default": False},
                 "skip_review": {"type": "boolean", "default": False},
                 "dry_run": {"type": "boolean", "default": False},
             }, "required": ["task"]}),
        Tool(name="run_explore",
             description="Run only the Explore subagent.",
             inputSchema={"type": "object", "properties": {
                 "task": {"type": "string"},
                 "repo_root": {"type": "string", "default": "."},
             }, "required": ["task"]}),
        Tool(name="run_plan",
             description="Run only the Plan subagent.",
             inputSchema={"type": "object", "properties": {
                 "task": {"type": "string"},
                 "repo_root": {"type": "string", "default": "."},
                 "explore_output": {"type": "string", "default": ""},
             }, "required": ["task"]}),
        Tool(name="run_task",
             description="Run only the Task subagent via headless Aider.",
             inputSchema={"type": "object", "properties": {
                 "task": {"type": "string"},
                 "repo_root": {"type": "string", "default": "."},
                 "plan": {"type": "string", "default": ""},
             }, "required": ["task"]}),
        Tool(name="web_search",
             description="Search the web via Tavily. Requires TAVILY_API_KEY.",
             inputSchema={"type": "object", "properties": {
                 "query": {"type": "string"},
                 "search_depth": {"type": "string", "enum": ["basic", "advanced"], "default": "basic"},
                 "max_results": {"type": "integer", "default": 5},
                 "include_domains": {"type": "array", "items": {"type": "string"}, "default": []},
                 "exclude_domains": {"type": "array", "items": {"type": "string"}, "default": []},
                 "topic": {"type": "string", "enum": ["general", "news"], "default": "general"},
             }, "required": ["query"]}),
        Tool(name="get_pipeline_status",
             description="Get current pipeline status from .aider-agents-state.json.",
             inputSchema={"type": "object", "properties": {
                 "repo_root": {"type": "string", "default": "."},
             }}),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    repo_root = arguments.get("repo_root", ".")
    task = arguments.get("task", "")
    try:
        if name == "run_agent_pipeline":
            pool = AgentPool(
                repo_root=Path(repo_root),
                api_key=os.environ.get("ANTHROPIC_API_KEY"),
                skip_explore=arguments.get("skip_explore", False),
                skip_review=arguments.get("skip_review", False),
                dry_run=arguments.get("dry_run", False),
            )
            result = pool.run(task)
            return [TextContent(type="text", text=json.dumps(result.to_dict(), indent=2))]
        elif name == "run_explore":
            pool = get_pool(repo_root)
            context = AgentContext(task=task, repo_root=Path(repo_root))
            result = pool.explore.run(context)
            return [TextContent(type="text", text=json.dumps(result.to_dict(), indent=2))]
        elif name == "run_plan":
            pool = get_pool(repo_root)
            context = AgentContext(task=task, repo_root=Path(repo_root),
                                   explore_output=arguments.get("explore_output", ""))
            result = pool.plan.run(context)
            return [TextContent(type="text", text=json.dumps(result.to_dict(), indent=2))]
        elif name == "run_task":
            pool = get_pool(repo_root)
            context = AgentContext(task=task, repo_root=Path(repo_root),
                                   plan=arguments.get("plan", ""))
            result = pool.task.run(context)
            return [TextContent(type="text", text=json.dumps(result.to_dict(), indent=2))]
        elif name == "web_search":
            from agents import WebSearchAgent
            agent = WebSearchAgent(
                api_key=os.environ.get("ANTHROPIC_API_KEY"),
                tavily_api_key=os.environ.get("TAVILY_API_KEY"),
                search_depth=arguments.get("search_depth", "basic"),
                max_results=arguments.get("max_results", 5),
            )
            summary = agent.search(
                query=arguments["query"],
                include_domains=arguments.get("include_domains", []),
                exclude_domains=arguments.get("exclude_domains", []),
                topic=arguments.get("topic", "general"),
            )
            if summary is None:
                return [TextContent(type="text", text='{"error": "Search returned no results"}')]
            return [TextContent(type="text", text=summary.to_markdown())]
        elif name == "get_pipeline_status":
            context = AgentContext.load(Path(repo_root))
            if context is None:
                return [TextContent(type="text", text='{"status": "no state found"}')]
            state = {
                "task": context.task,
                "review_status": context.review_status,
                "review_notes": context.review_notes,
                "plan_exists": bool(context.plan),
                "explore_done": bool(context.explore_output),
                "subtasks_completed": len(context.task_results),
            }
            return [TextContent(type="text", text=json.dumps(state, indent=2))]
        else:
            return [TextContent(type="text", text=f'{{"error": "Unknown tool: {name}"}')]
    except Exception as e:
        logger.exception(f"Tool {name} failed")
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def main():
    logging.basicConfig(level=logging.INFO)
    logger.info("aider-agents MCP server starting (stdio)")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
