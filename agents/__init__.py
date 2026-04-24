"""aider-agents - subagent system for Aider."""
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
