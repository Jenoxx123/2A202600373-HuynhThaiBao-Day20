"""Analyst agent implementation."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span
from multi_agent_research_lab.services.llm_client import LLMClient


class AnalystAgent(BaseAgent):
    """Turns research notes into structured insights."""

    name = "analyst"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.analysis_notes`."""

        research_notes = state.research_notes or "No research notes available."
        with trace_span("agent.analyst", {"query": state.request.query}) as span:
            response = self.llm_client.complete(
                system_prompt=(
                    "You are an analyst. Extract key claims, compare viewpoints, and "
                    "flag weak evidence. Keep output compact and structured."
                ),
                user_prompt=(
                    f"Query: {state.request.query}\n"
                    f"Audience: {state.request.audience}\n"
                    "Research notes:\n"
                    f"{research_notes}"
                ),
            )
            state.analysis_notes = response.content
            state.agent_results.append(
                AgentResult(
                    agent=AgentName.ANALYST,
                    content=response.content,
                    metadata={
                        "input_tokens": response.input_tokens,
                        "output_tokens": response.output_tokens,
                        "cost_usd": response.cost_usd,
                    },
                )
            )
            attributes = span.get("attributes")
            if isinstance(attributes, dict):
                attributes["cost_usd"] = response.cost_usd
        state.add_trace_event(
            "agent_result",
            {
                "agent": self.name,
                "cost_usd": response.cost_usd,
                "duration_seconds": span["duration_seconds"],
                "status": span["status"],
                "trace_provider": span["trace_provider"],
                "degraded": span["degraded"],
            },
        )
        return state
