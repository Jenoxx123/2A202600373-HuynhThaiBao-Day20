"""Benchmark helpers for single-agent vs multi-agent runs."""

from collections.abc import Callable
from time import perf_counter

from multi_agent_research_lab.core.schemas import BenchmarkMetrics
from multi_agent_research_lab.core.state import ResearchState

Runner = Callable[[str], ResearchState]


def run_benchmark(
    run_name: str, query: str, runner: Runner
) -> tuple[ResearchState, BenchmarkMetrics]:
    """Measure latency, estimate quality and cost, and return metrics."""

    started = perf_counter()
    state = runner(query)
    latency = perf_counter() - started
    metrics = BenchmarkMetrics(
        run_name=run_name,
        latency_seconds=latency,
        estimated_cost_usd=_estimate_total_cost(state),
        quality_score=_estimate_quality_score(state),
        notes=_build_notes(state),
    )
    return state, metrics


def _estimate_total_cost(state: ResearchState) -> float | None:
    costs: list[float] = []
    for result in state.agent_results:
        cost = result.metadata.get("cost_usd")
        if isinstance(cost, (int, float)):
            costs.append(float(cost))
    if not costs:
        return None
    return round(sum(costs), 6)


def _estimate_quality_score(state: ResearchState) -> float:
    score = 0.0
    if state.research_notes:
        score += 2.5
    if state.analysis_notes:
        score += 2.5
    if state.final_answer:
        score += 3.0
    if state.sources:
        score += 1.0
    if not state.errors:
        score += 1.0
    return min(10.0, score)


def _build_notes(state: ResearchState) -> str:
    source_count = len(state.sources)
    failure_rate = "0.00" if not state.errors else "1.00"
    trace_provider = _infer_trace_provider(state)
    degraded = _is_degraded(state)
    notes = (
        f"sources={source_count}; "
        f"trace_events={len(state.trace)}; "
        f"failure_rate={failure_rate}; "
        f"trace_provider={trace_provider}; "
        f"degraded={str(degraded).lower()}"
    )
    if state.errors:
        notes = f"{notes}; errors={' | '.join(state.errors[:2])}"
    return notes


def _infer_trace_provider(state: ResearchState) -> str:
    for event in state.trace:
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        provider = payload.get("trace_provider")
        if provider in {"langsmith", "local"}:
            return str(provider)
    return "local"


def _is_degraded(state: ResearchState) -> bool:
    for event in state.trace:
        payload = event.get("payload")
        if isinstance(payload, dict) and payload.get("degraded") is True:
            return True
    if state.final_answer and state.final_answer.startswith("Fallback response generated locally."):
        return True
    for result in state.agent_results:
        if result.content.startswith("Fallback response generated locally."):
            return True
    return False
