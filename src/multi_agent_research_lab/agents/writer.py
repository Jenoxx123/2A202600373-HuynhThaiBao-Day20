"""Writer agent implementation."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span
from multi_agent_research_lab.services.llm_client import LLMClient


class WriterAgent(BaseAgent):
    """Produces final answer from research and analysis notes."""

    name = "writer"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.final_answer`."""

        sources_summary = "\n".join(
            f"- {source.title}: {source.url or 'n/a'}" for source in state.sources[:5]
        )
        with trace_span("agent.writer", {"query": state.request.query}) as span:
            response = self.llm_client.complete(
                system_prompt=(
                    "You are a technical writer. Produce a concise answer grounded in "
                    "the provided analysis and include source references."
                ),
                user_prompt=(
                    f"Query: {state.request.query}\n"
                    f"Audience: {state.request.audience}\n"
                    f"Research notes:\n{state.research_notes or 'n/a'}\n\n"
                    f"Analysis notes:\n{state.analysis_notes or 'n/a'}\n\n"
                    f"Sources:\n{sources_summary}"
                ),
            )
            state.final_answer = response.content
            state.agent_results.append(
                AgentResult(
                    agent=AgentName.WRITER,
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
