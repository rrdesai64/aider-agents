"""WebSearchAgent - searches the web via Tavily and synthesises with Claude."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Optional

from .base import BaseAgent, AgentContext, AgentResult


@dataclass
class SearchResult:
    """A single result returned from a Tavily search."""
    title: str
    url: str
    content: str
    score: float = 0.0


@dataclass
class SearchSummary:
    """Aggregated search results with a Claude-generated synthesis."""
    query: str
    results: list = field(default_factory=list)
    synthesis: str = ""
    answer: str = ""          # Tavily include_answer field

    def to_markdown(self) -> str:
        """Render the summary as a markdown string."""
        lines = [f"## Web search: {self.query}\n"]
        if self.answer:
            lines += [f"**Quick answer:** {self.answer}\n"]
        lines += [self.synthesis, "\n### Sources\n"]
        for r in self.results:
            lines.append(f"- [{r.title}]({r.url})")
        return "\n".join(lines)


class WebSearchAgent(BaseAgent):
    """Agent that searches the web via Tavily and synthesises results with Claude."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        tavily_api_key: Optional[str] = None,
        search_depth: str = "basic",
        max_results: int = 5,
    ):
        """Initialise the WebSearchAgent with API keys and search parameters."""
        super().__init__(api_key=api_key, model_tier="cheap")
        self.tavily_api_key = tavily_api_key
        self.search_depth = search_depth
        self.max_results = max_results

    @property
    def system_prompt(self) -> str:
        """Return the system prompt for web search synthesis."""
        return (
            "You are WebSearchAgent. You synthesise web search results into a concise, "
            "accurate summary relevant to the given coding task. Focus on libraries, "
            "patterns, docs and best practices. Be concrete and brief."
        )

    def _get_client(self):
        """Return a TavilyClient, reading key from env if not explicitly set."""
        from tavily import TavilyClient
        if self.tavily_api_key:
            return TavilyClient(api_key=self.tavily_api_key)
        return TavilyClient()   # reads TAVILY_API_KEY from env

    def search(
        self,
        query: str,
        include_domains: Optional[list] = None,
        exclude_domains: Optional[list] = None,
        topic: str = "general",
        time_range: Optional[str] = None,
    ) -> Optional[SearchSummary]:
        """Run a Tavily search and return a SearchSummary, or None on failure."""
        try:
            client = self._get_client()
        except ImportError:
            return None

        # Best practice: keep queries under 400 chars
        query = query[:400]

        kwargs = dict(
            query=query,
            search_depth=self.search_depth,
            max_results=self.max_results,
            topic=topic,
            include_answer=True,        # get LLM-generated quick answer
            include_raw_content=False,  # keep token usage low
        )
        if include_domains:
            kwargs["include_domains"] = include_domains
        if exclude_domains:
            kwargs["exclude_domains"] = exclude_domains
        if time_range:
            kwargs["time_range"] = time_range

        try:
            response = client.search(**kwargs)
        except Exception:
            return None

        results = [
            SearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                content=r.get("content", ""),
                score=r.get("score", 0.0),
            )
            for r in response.get("results", [])
            if r.get("score", 0.0) > 0.3      # filter low-relevance results
        ]
        if not results:
            return None

        answer = response.get("answer", "")

        # Synthesise with Claude — use answer + top snippets to keep tokens low
        context_text = "\n\n".join(
            f"[{r.title}]({r.url})\n{r.content[:400]}"
            for r in results[:5]
        )
        synthesis_prompt = (
            f"Query: {query}\n\n"
            f"Tavily answer: {answer}\n\n"
            f"Top results:\n{context_text}\n\n"
            "Synthesise the key findings in 3-5 concise bullet points "
            "relevant to a coding task."
        )
        try:
            synthesis, _ = self._call_api(
                [{"role": "user", "content": synthesis_prompt}],
                max_tokens=512,
            )
        except Exception:
            synthesis = answer or "Search completed but synthesis failed."

        return SearchSummary(
            query=query,
            results=results,
            synthesis=synthesis,
            answer=answer,
        )

    def run(self, context: AgentContext) -> AgentResult:
        """Run web search for the task and store results in context metadata."""
        start = time.time()

        # Best practice: break compound task into focused query
        query = context.task[:400]

        summary = self.search(query, topic="general")
        if summary is None:
            # retry with news topic for recent/current topics
            summary = self.search(query, topic="news")

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
            output=f"Found {len(summary.results)} results (answer: {bool(summary.answer)})",
            data={"synthesis": summary.synthesis, "answer": summary.answer},
            duration_seconds=time.time() - start,
        )
