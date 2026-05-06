from multi_agent_research_lab.agents.analyst import AnalystAgent
from multi_agent_research_lab.agents.researcher import ResearcherAgent
from multi_agent_research_lab.agents.supervisor import SupervisorAgent
from multi_agent_research_lab.agents.writer import WriterAgent
from multi_agent_research_lab.core.schemas import ResearchQuery, SourceDocument
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.services.llm_client import LLMResponse


class StubSearchClient:
    def search(self, query: str, max_results: int = 5) -> list[SourceDocument]:
        return [
            SourceDocument(
                title="Workflow source",
                url="https://example.org/workflow",
                snippet=f"Workflow snippet for {query}",
            )
        ][:max_results]


class StubLLMClient:
    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        return LLMResponse(content=f"workflow::{system_prompt[:24]}")


def test_workflow_reaches_final_answer() -> None:
    workflow = MultiAgentWorkflow(
        supervisor=SupervisorAgent(),
        researcher=ResearcherAgent(search_client=StubSearchClient()),
        analyst=AnalystAgent(llm_client=StubLLMClient()),
        writer=WriterAgent(llm_client=StubLLMClient()),
    )
    state = ResearchState(request=ResearchQuery(query="When to use multi-agent systems?"))
    result = workflow.run(state)
    assert result.final_answer is not None
    assert "done" in result.route_history
    assert result.iteration <= 6
