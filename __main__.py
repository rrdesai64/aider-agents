"""
aider-agents CLI
"""
from __future__ import annotations
from dotenv import load_dotenv
load_dotenv()
import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path


def main():
    """Parse command-line arguments and run the aider-agents system or MCP server."""
    parser = argparse.ArgumentParser(
        prog="aider-agents",
        description="Subagent system for Aider - Explore, Plan, Task, Review",
    )
    parser.add_argument("task", nargs="?", help="Natural language task description")
    parser.add_argument("--repo-root", default=".", help="Path to repository root")
    parser.add_argument("--skip-explore", action="store_true")
    parser.add_argument("--skip-review", action="store_true")
    parser.add_argument("--skip-web-search", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-commit", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--mcp-server", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--output-json", action="store_true")
    args = parser.parse_args()

    if args.mcp_server:
        from mcp_server import main as mcp_main
        asyncio.run(mcp_main())
        return

    if not args.task and not args.resume:
        parser.print_help()
        sys.exit(1)

    from orchestrator import AgentPool
    pool = AgentPool(
        repo_root=Path(args.repo_root),
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
        auto_commit=not args.no_commit,
        dry_run=args.dry_run,
        skip_explore=args.skip_explore,
        skip_web_search=args.skip_web_search,
        skip_review=args.skip_review,
        verbose=args.verbose,
    )
    task = args.task or "(resuming)"
    result = pool.run(task, resume=args.resume)
    if args.output_json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        status = "SUCCESS" if result.success else "FAILED"
        print(f"\n{status}: {result.output}")
        if result.error:
            print(f"Error: {result.error}")
    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
