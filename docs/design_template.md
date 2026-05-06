# Design Template

## Problem

Build a research assistant that can handle long-form technical questions with transparent
handoffs between roles: collecting evidence, analyzing claims, and writing a final answer.

## Why multi-agent?

Single-agent answers are fast but often blur role boundaries. A multi-agent flow improves
control and debuggability by splitting work into focused steps with traceable state updates.

## Agent roles

| Agent | Responsibility | Input | Output | Failure mode |
|---|---|---|---|---|
| Supervisor | Decide next route and stop condition | Current `ResearchState` | `route_history` update | Wrong route leads to missing notes |
| Researcher | Gather and summarize sources | Query + max sources | `sources`, `research_notes` | Empty/low-quality sources |
| Analyst | Turn notes into structured insights | `research_notes` | `analysis_notes` | Weak claim separation |
| Writer | Produce final user-facing answer | Query + notes + sources | `final_answer` | Missing citations or vague conclusions |

## Shared state

`ResearchState` carries request, route history, notes, final answer, per-agent outputs,
trace events, and errors. This is enough for workflow handoff, debugging, and benchmark
extraction without hidden side channels.

## Routing policy

`Supervisor` decision order:

1. If max iterations reached -> `done`
2. If `research_notes` missing -> `researcher`
3. If `analysis_notes` missing -> `analyst`
4. If `final_answer` missing -> `writer`
5. Otherwise -> `done`

Graph shape: `START -> supervisor -> {researcher|analyst|writer|END}` and each worker
returns to `supervisor`.

## Guardrails

- Max iterations: configured from `MAX_ITERATIONS` (default 6)
- Timeout: provider clients use `TIMEOUT_SECONDS`
- Retry: OpenAI and Tavily calls retry with exponential backoff
- Fallback: deterministic local response/search when API key or network is unavailable
- Validation: schema validation through Pydantic models and typed state transitions

## Benchmark plan

Queries are loaded from `configs/lab_default.yaml`. For each query, run both baseline and
multi-agent workflows, then compare:

- Latency (seconds)
- Estimated cost (USD, when token usage is available)
- Quality score heuristic (0-10)
- Failure notes (errors and trace health)
