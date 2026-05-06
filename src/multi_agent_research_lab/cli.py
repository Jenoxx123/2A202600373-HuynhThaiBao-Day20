"""Command-line entrypoint for the lab starter."""

from pathlib import Path
from typing import Annotated

import typer
import yaml
from rich.console import Console
from rich.panel import Panel

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.schemas import ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.benchmark import run_benchmark
from multi_agent_research_lab.evaluation.report import render_markdown_report
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.observability.logging import configure_logging
from multi_agent_research_lab.observability.tracing import trace_span
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.storage import LocalArtifactStore

app = typer.Typer(help="Multi-Agent Research Lab starter CLI")
console = Console()


def _init() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)


def _run_baseline(query: str) -> ResearchState:
    request = ResearchQuery(query=query)
    state = ResearchState(request=request)
    llm = LLMClient()
    prompt = (
        f"Query: {request.query}\n"
        f"Audience: {request.audience}\n"
        "Write a concise and useful answer in markdown."
    )
    with trace_span("agent.baseline", {"query": request.query}) as span:
        response = llm.complete(
            system_prompt="You are a single-agent research assistant.",
            user_prompt=prompt,
        )
    state.final_answer = response.content
    is_fallback = response.content.startswith("Fallback response generated locally.")
    state.add_trace_event(
        "baseline",
        {
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "cost_usd": response.cost_usd,
            "trace_provider": span["trace_provider"],
            "degraded": bool(span["degraded"] or is_fallback),
        },
    )
    return state


def _run_multi(query: str) -> ResearchState:
    state = ResearchState(request=ResearchQuery(query=query))
    workflow = MultiAgentWorkflow()
    return workflow.run(state)


@app.command()
def baseline(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run a minimal single-agent baseline."""

    _init()
    state = _run_baseline(query)
    console.print(Panel.fit(state.final_answer or "", title="Single-Agent Baseline"))


@app.command("multi-agent")
def multi_agent(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run the multi-agent workflow."""

    _init()
    result = _run_multi(query)
    console.print(result.model_dump_json(indent=2))


@app.command()
def benchmark(
    config: Annotated[
        str, typer.Option("--config", help="Path to YAML config")
    ] = "configs/lab_default.yaml",
) -> None:
    """Run baseline and multi-agent benchmark, then write markdown report."""

    _init()
    config_path = Path(config)
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    queries: list[str] = payload.get("benchmark", {}).get("queries", [])
    metrics = []
    for query in queries:
        _, baseline_metrics = run_benchmark("baseline", query, _run_baseline)
        _, multi_metrics = run_benchmark("multi-agent", query, _run_multi)
        metrics.extend([baseline_metrics, multi_metrics])
    report = render_markdown_report(metrics)
    path = LocalArtifactStore().write_text("benchmark_report.md", report)
    console.print(Panel.fit(f"Benchmark report written: {path}", title="Benchmark"))


if __name__ == "__main__":
    app()
