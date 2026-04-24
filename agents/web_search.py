"""WebSearchAgent - searches the web via Tavily and synthesises with Claude."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Optional

from .base import BaseAgent, AgentContext, AgentResult


@dataclass
class SearchResult:
    title: str
    url: str
    content: str
    score: float = 0.0


@dataclass
class SearchSummary:
    query: str
    results: list = field(default_factory=list)
    synthesis: str = ""

    def to_markdown(self) -> str:
        """Convert search summary to markdown format."""
        lines = [f"## Web search: {self.query}\n", self.synthesis, "\n### Sources\n"]
        for r in self.results:
            lines.append(f"- [{r.title}]({r.url})")
        return "\n".join(lines)


class WebSearchAgent(BaseAgent):
    def __init__(
        self,
        api_key: Optional[str] = None,
        tavily_api_key: Optional[str] = None,
        search_depth: str = "basic",
        max_results: int = 5,
    ):
        super().__init__(api_key=api_key, model_tier="cheap")
        self.tavily_api_key = tavily_api_key
        self.search_depth = search_depth
        self.max_results = max_results

    @property
    def system_prompt(self) -> str:
        return (
            "You are WebSearchAgent. You synthesise web search results into a concise, "
            "accurate summary relevant to the given coding task. Focus on libraries, "
            "patterns, docs and best practices. Be concrete and brief."
        )

    def search(
        self,
        query: str,
        include_domains: Optional[list] = None,
        exclude_domains: Optional[list] = None,
        topic: str = "general",
    ) -> Optional[SearchSummary]:
        """Search the web using Tavily and synthesize results."""
        try:
            from tavily import TavilyClient
        except ImportError:
            return None

        client = TavilyClient(api_key=self.tavily_api_key)
        kwargs = dict(
            query=query,
            search_depth=self.search_depth,
            max_results=self.max_results,
            topic=topic,
        )
        if include_domains:
            kwargs["include_domains"] = include_domains
        if exclude_domains:
            kwargs["exclude_domains"] = exclude_domains

        response = client.search(**kwargs)
        results = [
            SearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                content=r.get("content", ""),
                score=r.get("score", 0.0),
            )
            for r in response.get("results", [])
        ]
        if not results:
            return None

        context_text = "\n\n".join(
            f"[{r.title}]({r.url})\n{r.content[:500]}" for r in results
        )
        synthesis, _ = self._call_api(
            [{"role": "user", "content": (
                f"Query: {query}\n\nResults:\n{context_text}\n\n"
                "Synthesise the key findings in 3-5 concise bullet points."
            )}],
            max_tokens=1024,
        )
        return SearchSummary(query=query, results=results, synthesis=synthesis)

    def run(self, context: AgentContext) -> AgentResult:
        """Execute web search for the given task context."""
        start = time.time()
        summary = self.search(context.task)
        if summary is None:
            return AgentResult(
                agent_type="web_search",
                success=False,
                output="No results or Tavily not available",
                duration_seconds=time.time() - start,
            )
        context.metadata["web_search_results"] = summary.to_markdown()
        context.save()
        return AgentResult(
            agent_type="web_search",
            success=True,
            output=f"Found {len(summary.results)} results",
            data={"synthesis": summary.synthesis},
            duration_seconds=time.time() - start,
        )
