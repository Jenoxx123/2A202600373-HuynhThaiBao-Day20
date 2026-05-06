from contextlib import contextmanager

import pytest

from multi_agent_research_lab.observability import tracing


def test_trace_span_records_duration_and_ok_status() -> None:
    with tracing.trace_span("unit.test", {"k": "v"}) as span:
        assert span["name"] == "unit.test"
    assert span["duration_seconds"] is not None
    assert span["status"] == "ok"


def test_trace_span_records_error_status() -> None:
    with pytest.raises(RuntimeError), tracing.trace_span("unit.error"):
        raise RuntimeError("boom")


def test_trace_span_local_fallback_when_langsmith_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tracing, "_LANGSMITH_DISABLED", True)
    with tracing.trace_span("unit.local") as span:
        pass
    assert span["trace_provider"] == "local"


def test_trace_span_uses_langsmith_when_available(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeRunTree:
        def end(self, **kwargs: object) -> None:
            return None

    @contextmanager
    def fake_langsmith_trace(name: str, attributes: dict[str, object], settings: object):
        yield FakeRunTree()

    monkeypatch.setattr(tracing, "_LANGSMITH_DISABLED", False)
    monkeypatch.setattr(tracing, "_should_use_langsmith", lambda settings: True)
    monkeypatch.setattr(tracing, "_langsmith_trace", fake_langsmith_trace)
    with tracing.trace_span("unit.langsmith", {"k": "v"}) as span:
        pass
    assert span["trace_provider"] == "langsmith"
