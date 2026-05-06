from multi_agent_research_lab.agents.analyst import AnalystAgent
from multi_agent_research_lab.agents.researcher import ResearcherAgent
from multi_agent_research_lab.agents.supervisor import SupervisorAgent
from multi_agent_research_lab.agents.writer import WriterAgent
from multi_agent_research_lab.core.schemas import ResearchQuery, SourceDocument
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMResponse


class StubSearchClient:
    def search(self, query: str, max_results: int = 5) -> list[SourceDocument]:
        return [
            SourceDocument(
                title="Stub source",
                url="https://example.org/stub",
                snippet=f"Snippet for {query}",
            )
        ][:max_results]


class StubLLMClient:
    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        return LLMResponse(content=f"stub-output::{system_prompt[:20]}")


def test_supervisor_routes_in_expected_order() -> None:
    supervisor = SupervisorAgent()
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent systems"))
    state = supervisor.run(state)
    assert state.route_history[-1] == "researcher"
    state.research_notes = "ready"
    state = supervisor.run(state)
    assert state.route_history[-1] == "analyst"
    state.analysis_notes = "ready"
    state = supervisor.run(state)
    assert state.route_history[-1] == "writer"
    state.final_answer = "ready"
    state = supervisor.run(state)
    assert state.route_history[-1] == "done"


def test_worker_agents_update_state() -> None:
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent systems"))
    researcher = ResearcherAgent(search_client=StubSearchClient())
    analyst = AnalystAgent(llm_client=StubLLMClient())
    writer = WriterAgent(llm_client=StubLLMClient())

    state = researcher.run(state)
    assert state.sources
    assert state.research_notes is not None

    state = analyst.run(state)
    assert state.analysis_notes is not None

    state = writer.run(state)
    assert state.final_answer is not None
    assert len(state.agent_results) == 3
