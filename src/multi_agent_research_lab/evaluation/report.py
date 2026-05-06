"""Benchmark report rendering."""

from multi_agent_research_lab.core.schemas import BenchmarkMetrics


def render_markdown_report(metrics: list[BenchmarkMetrics]) -> str:
    """Render benchmark metrics to markdown."""

    lines = [
        "# Benchmark Report",
        "",
        "| Run | Latency (s) | Cost (USD) | Quality | Notes |",
        "|---|---:|---:|---:|---|",
    ]
    for item in metrics:
        cost = "" if item.estimated_cost_usd is None else f"{item.estimated_cost_usd:.4f}"
        quality = "" if item.quality_score is None else f"{item.quality_score:.1f}"
        lines.append(
            f"| {item.run_name} | {item.latency_seconds:.2f} | {cost} | {quality} | {item.notes} |"
        )

    baselines = [item for item in metrics if item.run_name == "baseline"]
    multi_agents = [item for item in metrics if item.run_name == "multi-agent"]
    langsmith_runs = sum(1 for item in metrics if "trace_provider=langsmith" in item.notes)
    local_runs = sum(1 for item in metrics if "trace_provider=local" in item.notes)
    degraded_runs = sum(1 for item in metrics if "degraded=true" in item.notes)
    lines.extend(["", "## Summary"])
    lines.append(f"- Runs: {len(metrics)}")
    lines.append(f"- Baseline runs: {len(baselines)}")
    lines.append(f"- Multi-agent runs: {len(multi_agents)}")
    lines.append(f"- LangSmith traced runs: {langsmith_runs}")
    lines.append(f"- Local traced runs: {local_runs}")
    lines.append(f"- Degraded runs: {degraded_runs}")
    lines.append("- Interpretation: lower latency/cost is better, higher quality is better.")
    lines.append("")
    return "\n".join(lines)
