# Lab Guide: Multi-Agent Research System

## Scenario

You need a research assistant that can handle long queries, collect information, analyze it,
and write a final response. The lab compares:

1. **Single-agent baseline**: one agent does everything.
2. **Multi-agent workflow**: Supervisor orchestrates Researcher, Analyst, Writer.

## Important rules

- Do not add agents without a clear reason.
- Keep each agent responsibility distinct.
- Shared state must be explicit enough for debugging.
- Keep trace/logs for each step.
- Benchmark with measurable metrics, not intuition only.

## Milestone 1: Baseline

Suggested files:

- `src/multi_agent_research_lab/cli.py`
- `src/multi_agent_research_lab/services/llm_client.py`

Implementation target: replace baseline placeholder with a real LLM call and fallback.

## Milestone 2: Supervisor

Suggested files:

- `src/multi_agent_research_lab/agents/supervisor.py`
- `src/multi_agent_research_lab/graph/workflow.py`

Implementation target: deterministic routing policy with max-iteration stop condition.

## Milestone 3: Worker agents

Suggested files:

- `agents/researcher.py`
- `agents/analyst.py`
- `agents/writer.py`

Implementation target: each worker writes its own outputs into shared state and trace.

## Milestone 4: Trace and benchmark

Suggested files:

- `observability/tracing.py`
- `evaluation/benchmark.py`
- `evaluation/report.py`

Minimum benchmark metrics:

| Metric | Suggested measurement |
|---|---|
| Latency | wall-clock time |
| Cost | token usage or provider usage |
| Quality | rubric score 0-10 |
| Citation coverage | sourced claims / total key claims |
| Failure rate | failed queries / total queries |

## Exit ticket

Each team should answer:

1. Which cases should use multi-agent workflows? Why?
2. Which cases should not use multi-agent workflows? Why?
