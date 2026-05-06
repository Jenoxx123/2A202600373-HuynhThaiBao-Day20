"""Supervisor / router implementation."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.schemas import AgentName
from multi_agent_research_lab.core.state import ResearchState


class SupervisorAgent(BaseAgent):
    """Decides which worker should run next and when to stop."""

    name = "supervisor"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def run(self, state: ResearchState) -> ResearchState:
        """Update `state.route_history` with the next route."""

        route = self._decide_next_route(state)
        state.record_route(route)
        state.add_trace_event(
            "route",
            {
                "agent": self.name,
                "next": route,
                "iteration": state.iteration,
            },
        )
        return state

    def _decide_next_route(self, state: ResearchState) -> str:
        if state.iteration >= self.settings.max_iterations:
            state.errors.append("Reached max_iterations, forcing stop.")
            return "done"
        if not state.research_notes:
            return AgentName.RESEARCHER.value
        if not state.analysis_notes:
            return AgentName.ANALYST.value
        if not state.final_answer:
            return AgentName.WRITER.value
        return "done"
