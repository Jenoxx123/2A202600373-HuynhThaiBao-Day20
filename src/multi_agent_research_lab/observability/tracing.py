"""Tracing hooks with LangSmith support and local fallback."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from time import perf_counter
from typing import Any

from multi_agent_research_lab.core.config import Settings, get_settings

_LANGSMITH_DISABLED = False
_LAST_PROVIDER = "local"
_LAST_PROVIDER_DEGRADED = False


def get_tracing_status() -> dict[str, Any]:
    """Expose current tracing provider status for reporting."""

    return {
        "provider": _LAST_PROVIDER,
        "degraded": _LAST_PROVIDER_DEGRADED,
        "langsmith_disabled": _LANGSMITH_DISABLED,
    }


def _mark_status(provider: str, degraded: bool) -> None:
    global _LAST_PROVIDER, _LAST_PROVIDER_DEGRADED
    _LAST_PROVIDER = provider
    _LAST_PROVIDER_DEGRADED = degraded


def _disable_langsmith() -> None:
    global _LANGSMITH_DISABLED
    _LANGSMITH_DISABLED = True
    _mark_status("local", True)


def _should_use_langsmith(settings: Settings) -> bool:
    if _LANGSMITH_DISABLED:
        return False
    return bool(settings.langsmith_api_key)


@contextmanager
def _langsmith_trace(
    name: str, attributes: dict[str, Any], settings: Settings
) -> Iterator[Any]:
    from langsmith import Client
    from langsmith.run_helpers import trace, tracing_context

    client = Client(api_key=settings.langsmith_api_key)
    # Force-enable tracing in this scope even if LANGSMITH_TRACING is unset.
    with tracing_context(enabled=True), trace(
        name=name,
        run_type="chain",
        inputs=attributes,
        project_name=settings.langsmith_project,
        client=client,
        metadata={"component": "multi-agent-research-lab", **attributes},
        tags=["multi-agent-research-lab"],
    ) as run_tree:
        yield run_tree


@contextmanager
def trace_span(name: str, attributes: dict[str, Any] | None = None) -> Iterator[dict[str, Any]]:
    """Create a span that prefers LangSmith and falls back to local tracing."""

    settings = get_settings()
    started = perf_counter()
    span: dict[str, Any] = {
        "name": name,
        "attributes": attributes or {},
        "status": "ok",
        "error": None,
        "duration_seconds": None,
        "trace_provider": "local",
        "degraded": False,
    }

    if _should_use_langsmith(settings):
        try:
            with _langsmith_trace(name, span["attributes"], settings) as run_tree:
                span["trace_provider"] = "langsmith"
                _mark_status("langsmith", False)
                try:
                    yield span
                except Exception as exc:
                    span["status"] = "error"
                    span["error"] = str(exc)
                    raise
                finally:
                    span["duration_seconds"] = perf_counter() - started
                    # Enrich LangSmith run with execution outcome.
                    run_tree.end(
                        outputs={
                            "status": span["status"],
                            "error": span["error"],
                            "duration_seconds": span["duration_seconds"],
                            "trace_provider": span["trace_provider"],
                            "degraded": span["degraded"],
                        },
                        metadata={
                            "component": "multi-agent-research-lab",
                            "trace_provider": span["trace_provider"],
                            "degraded": span["degraded"],
                        },
                    )
            return
        except Exception:
            _disable_langsmith()
            span["trace_provider"] = "local"
            span["degraded"] = True

    _mark_status("local", _LAST_PROVIDER_DEGRADED)
    try:
        yield span
    except Exception as exc:
        span["status"] = "error"
        span["error"] = str(exc)
        raise
    finally:
        span["duration_seconds"] = perf_counter() - started
