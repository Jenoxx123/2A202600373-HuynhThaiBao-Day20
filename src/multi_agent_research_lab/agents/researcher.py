"""Researcher agent implementation."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span
from multi_agent_research_lab.services.search_client import SearchClient


class ResearcherAgent(BaseAgent):
    """Collects sources and creates concise research notes."""

    name = "researcher"

    def __init__(self, search_client: SearchClient | None = None) -> None:
        self.search_client = search_client or SearchClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.sources` and `state.research_notes`."""

        with trace_span("agent.researcher", {"query": state.request.query}) as span:
            sources = self.search_client.search(
                query=state.request.query,
                max_results=state.request.max_sources,
            )
            state.sources = sources
            notes_lines = ["Research notes:"]
            for source in sources:
                url = source.url or "n/a"
                notes_lines.append(f"- {source.title} ({url}): {source.snippet}")
            state.research_notes = "\n".join(notes_lines)
            state.agent_results.append(
                AgentResult(
                    agent=AgentName.RESEARCHER,
                    content=state.research_notes,
                    metadata={"source_count": len(sources)},
                )
            )
            attributes = span.get("attributes")
            if isinstance(attributes, dict):
                attributes["source_count"] = len(sources)
        state.add_trace_event(
            "agent_result",
            {
                "agent": self.name,
                "source_count": len(state.sources),
                "duration_seconds": span["duration_seconds"],
                "status": span["status"],
                "trace_provider": span["trace_provider"],
                "degraded": span["degraded"],
            },
        )
        return state
