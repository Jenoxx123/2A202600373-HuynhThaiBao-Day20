"""LangGraph workflow implementation."""

from typing import Any

from multi_agent_research_lab.agents.analyst import AnalystAgent
from multi_agent_research_lab.agents.researcher import ResearcherAgent
from multi_agent_research_lab.agents.supervisor import SupervisorAgent
from multi_agent_research_lab.agents.writer import WriterAgent
from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span


class MultiAgentWorkflow:
    """Builds and runs the multi-agent graph.

    Keep orchestration here; keep agent internals in `agents/`.
    """

    def __init__(
        self,
        supervisor: SupervisorAgent | None = None,
        researcher: ResearcherAgent | None = None,
        analyst: AnalystAgent | None = None,
        writer: WriterAgent | None = None,
    ) -> None:
        self.supervisor = supervisor or SupervisorAgent()
        self.researcher = researcher or ResearcherAgent()
        self.analyst = analyst or AnalystAgent()
        self.writer = writer or WriterAgent()

    def build(self) -> object:
        """Create a LangGraph graph."""

        try:
            from langgraph.graph import END, START, StateGraph
        except ImportError:
            return self._run_without_langgraph

        graph = StateGraph(dict[str, Any])
        graph.add_node("supervisor", self._node_supervisor)
        graph.add_node("researcher", self._node_researcher)
        graph.add_node("analyst", self._node_analyst)
        graph.add_node("writer", self._node_writer)
        graph.add_edge(START, "supervisor")
        graph.add_conditional_edges(
            "supervisor",
            self._route_after_supervisor,
            {
                "researcher": "researcher",
                "analyst": "analyst",
                "writer": "writer",
                "done": END,
            },
        )
        graph.add_edge("researcher", "supervisor")
        graph.add_edge("analyst", "supervisor")
        graph.add_edge("writer", "supervisor")
        return graph.compile()

    def run(self, state: ResearchState) -> ResearchState:
        """Execute the graph and return final state."""

        with trace_span("workflow.multi_agent", {"query": state.request.query}) as span:
            app = self.build()
            if hasattr(app, "invoke"):
                output = app.invoke(state.model_dump())
                result = ResearchState.model_validate(output)
            elif callable(app):
                result = app(state)
            else:
                raise TypeError("Workflow build() returned unsupported app type.")
            result.add_trace_event(
                "workflow",
                {
                    "name": "workflow.multi_agent",
                    "trace_provider": span["trace_provider"],
                    "degraded": span["degraded"],
                    "status": span["status"],
                },
            )
            return result

    def _node_supervisor(self, payload: dict[str, Any]) -> dict[str, Any]:
        state = ResearchState.model_validate(payload)
        next_state = self.supervisor.run(state)
        return next_state.model_dump()

    def _node_researcher(self, payload: dict[str, Any]) -> dict[str, Any]:
        state = ResearchState.model_validate(payload)
        next_state = self.researcher.run(state)
        return next_state.model_dump()

    def _node_analyst(self, payload: dict[str, Any]) -> dict[str, Any]:
        state = ResearchState.model_validate(payload)
        next_state = self.analyst.run(state)
        return next_state.model_dump()

    def _node_writer(self, payload: dict[str, Any]) -> dict[str, Any]:
        state = ResearchState.model_validate(payload)
        next_state = self.writer.run(state)
        return next_state.model_dump()

    def _route_after_supervisor(self, payload: dict[str, Any]) -> str:
        history = payload.get("route_history", [])
        if not history:
            return "done"
        route = history[-1]
        if route in {"researcher", "analyst", "writer", "done"}:
            return route
        return "done"

    def _run_without_langgraph(self, state: ResearchState) -> ResearchState:
        settings = get_settings()
        while state.iteration < settings.max_iterations:
            state = self.supervisor.run(state)
            route = state.route_history[-1]
            if route == "done":
                break
            if route == "researcher":
                state = self.researcher.run(state)
            elif route == "analyst":
                state = self.analyst.run(state)
            elif route == "writer":
                state = self.writer.run(state)
            else:
                state.errors.append(f"Unknown route: {route}")
                break
        if not state.final_answer:
            state.final_answer = "Workflow ended without final answer."
        return state
