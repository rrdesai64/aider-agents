"""aider-agents - subagent system for Aider.

Exports:
    AgentContext: Shared state and configuration for agent execution.
    AgentResult: Return value containing agent execution results.
    MODEL_ROUTING: Configuration mapping model tiers to specific models.
    ExploreAgent: Agent that explores repository structure and context.
    PlanAgent: Agent that creates execution plans from tasks.
    TaskAgent: Agent that executes individual subtasks.
    ReviewAgent: Agent that reviews and validates task results.
    WebSearchAgent: Agent that performs web searches via Tavily API.
    SearchSummary: Aggregated and synthesized search results.
    SearchResult: Individual search result from web queries.
"""
from .base import AgentContext, AgentResult, MODEL_ROUTING
from .explore import ExploreAgent
from .plan import PlanAgent
from .task import TaskAgent
from .review import ReviewAgent
from .web_search import WebSearchAgent, SearchSummary, SearchResult

__all__ = [
    "AgentContext", "AgentResult", "MODEL_ROUTING",
    "ExploreAgent", "PlanAgent", "TaskAgent",
    "ReviewAgent", "WebSearchAgent", "SearchSummary", "SearchResult",
]
