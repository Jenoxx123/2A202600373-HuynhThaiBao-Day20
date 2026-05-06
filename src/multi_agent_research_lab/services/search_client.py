"""Search client abstraction for ResearcherAgent."""

from __future__ import annotations

import json
from urllib.error import URLError
from urllib.request import Request, urlopen

from tenacity import RetryError, retry, stop_after_attempt, wait_exponential

from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.schemas import SourceDocument


class SearchClient:
    """Provider-agnostic search client with Tavily + local fallback."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def search(self, query: str, max_results: int = 5) -> list[SourceDocument]:
        """Search for documents relevant to a query."""

        if not self.settings.tavily_api_key:
            return self._mock_search(query, max_results=max_results)
        try:
            docs = self._search_tavily(query, max_results=max_results)
            if docs:
                return docs
            return self._mock_search(query, max_results=max_results)
        except RetryError:
            return self._mock_search(query, max_results=max_results)
        except (OSError, URLError, ValueError, KeyError):
            return self._mock_search(query, max_results=max_results)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def _search_tavily(self, query: str, max_results: int) -> list[SourceDocument]:
        payload = json.dumps(
            {
                "api_key": self.settings.tavily_api_key,
                "query": query,
                "max_results": max_results,
                "search_depth": "basic",
            }
        ).encode("utf-8")
        request = Request(
            url="https://api.tavily.com/search",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=self.settings.timeout_seconds) as response:
            raw = response.read().decode("utf-8")
        data = json.loads(raw)
        results = data.get("results", [])
        docs: list[SourceDocument] = []
        for item in results[:max_results]:
            docs.append(
                SourceDocument(
                    title=item.get("title") or "Untitled",
                    url=item.get("url"),
                    snippet=(item.get("content") or item.get("snippet") or "").strip(),
                    metadata={"provider": "tavily", "score": item.get("score")},
                )
            )
        return docs

    def _mock_search(self, query: str, max_results: int) -> list[SourceDocument]:
        templates = [
            (
                "Multi-agent design patterns",
                "https://example.org/multi-agent-patterns",
                "Discusses supervisor-worker decomposition, role boundaries, and routing.",
            ),
            (
                "LLM guardrails in production",
                "https://example.org/llm-guardrails",
                "Covers retries, timeouts, fallback behavior, and output validation.",
            ),
            (
                "Evaluating agentic systems",
                "https://example.org/agent-eval",
                "Compares latency, cost, failure rate, and quality metrics in benchmarks.",
            ),
            (
                "Traceability for AI workflows",
                "https://example.org/ai-tracing",
                "Shows span-based tracing and per-step observability for debugging.",
            ),
            (
                "Source-grounded writing",
                "https://example.org/source-grounded-writing",
                "Best practices for citation-style writing using structured research notes.",
            ),
        ]
        docs: list[SourceDocument] = []
        for idx, (title, url, snippet) in enumerate(templates[:max_results], start=1):
            docs.append(
                SourceDocument(
                    title=f"{title} ({idx})",
                    url=url,
                    snippet=f"{snippet} Query focus: {query}",
                    metadata={"provider": "mock", "rank": idx},
                )
            )
        return docs
