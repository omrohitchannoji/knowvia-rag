"""
Unit tests for Langfuse v5 tracing integration using a mocked Langfuse client.
Does NOT require real Langfuse API credentials.
"""

from unittest.mock import MagicMock, patch
from backend.app.tracing.tracer import PipelineTracer
from backend.app.core.config import settings


def _make_mock_langfuse():
    mock_client = MagicMock()
    mock_client.create_trace_id.return_value = "a" * 32

    mock_root_span = MagicMock()
    created_children = []

    def _start_child(**kwargs):
        child = MagicMock()
        child.captured_kwargs = kwargs
        created_children.append(child)
        return child

    mock_root_span.start_observation.side_effect = _start_child
    mock_client.start_observation.return_value = mock_root_span
    return mock_client, mock_root_span, created_children


def test_langfuse_live_trace_and_seven_nested_observations():
    """Verify one root trace + 7 nested stage observations + flush with mocked Langfuse client."""
    mock_client, mock_root_span, created_children = _make_mock_langfuse()

    with patch("backend.app.tracing.tracer.get_langfuse_client", return_value=mock_client):
        tracer = PipelineTracer(trace_id="trace_unit_001", mode="rag_query")
        assert tracer.langfuse_mode == "live"
        assert tracer.langfuse_trace_id == "a" * 32

        tracer.record_span("guardrail", 0.5, details={"is_safe": True})
        tracer.record_span("router", 12.3, details={"intent": "knowledge"})
        tracer.record_span("dense_retrieval", 45.1, details={"candidates_retrieved": 10})
        tracer.record_span("bm25_retrieval", 8.2, details={"candidates_retrieved": 10})
        tracer.record_span("fusion", 0.4, details={"method": "rrf", "fused_candidates": 5})
        tracer.record_span("reranking", 120.0, details={"candidates_reranked": 5})
        tracer.record_llm_usage("openai/gpt-oss-20b", prompt_tokens=150, completion_tokens=45, usage_available=True)
        tracer.record_span("generation", 310.0, details={"evidence_status": "STRONG", "is_abstained": False})

        trace = tracer.finalize()

    assert trace.langfuse_mode == "live"
    assert len(created_children) == 7
    stage_names = [c.captured_kwargs["name"] for c in created_children]
    assert stage_names == [
        "guardrail",
        "router",
        "dense_retrieval",
        "bm25_retrieval",
        "fusion",
        "reranking",
        "generation",
    ]

    # Verify generation observation received real provider token usage and no raw input/output
    gen_kwargs = created_children[-1].captured_kwargs
    assert gen_kwargs["as_type"] == "generation"
    assert gen_kwargs["model"] == "openai/gpt-oss-20b"
    assert gen_kwargs["usage_details"] == {"input": 150, "output": 45, "total": 195}
    assert "input" not in gen_kwargs
    assert "output" not in gen_kwargs

    # Verify cost is computed from configured MODEL_PRICING for openai/gpt-oss-20b
    assert trace.estimated_cost_usd == 2.5e-05
    assert trace.cost_calculation_details["cost_available"] is True

    # Verify root span updated, ended, and client flushed
    assert mock_root_span.update.called
    assert mock_root_span.end.called
    assert mock_client.flush.called
    for child in created_children:
        assert child.end.called


def test_langfuse_missing_usage_marked_unavailable():
    """When provider omits usage, generation span marks token_usage='unavailable' and omits usage_details."""
    mock_client, _, created_children = _make_mock_langfuse()

    with patch("backend.app.tracing.tracer.get_langfuse_client", return_value=mock_client):
        tracer = PipelineTracer(trace_id="trace_unit_002")
        tracer.record_llm_usage("mock-offline", prompt_tokens=None, completion_tokens=None, usage_available=False)
        tracer.record_span("generation", 10.0, details={"is_abstained": False})
        trace = tracer.finalize()

    gen_kwargs = created_children[0].captured_kwargs
    assert "usage_details" not in gen_kwargs
    assert gen_kwargs["metadata"]["token_usage"] == "unavailable"
    assert trace.token_usage.usage_available is False
    assert trace.estimated_cost_usd is None


def test_router_and_generation_usage_are_aggregated_and_recorded_per_stage():
    """Both LLM calls in one query contribute tokens and retain per-stage usage."""
    mock_client, _, created_children = _make_mock_langfuse()

    with patch("backend.app.tracing.tracer.get_langfuse_client", return_value=mock_client):
        tracer = PipelineTracer(trace_id="trace_unit_usage_aggregate")
        tracer.record_llm_usage(
            "openai/gpt-oss-20b", 80, 20, total_tokens=100,
            usage_available=True, stage="router",
        )
        tracer.record_span("router", 15.0, details={"intent": "knowledge"})
        tracer.record_llm_usage(
            "openai/gpt-oss-20b", 150, 45, total_tokens=195,
            usage_available=True, stage="generation",
        )
        tracer.record_span("generation", 300.0, details={"is_abstained": False})
        trace = tracer.finalize()

    assert trace.token_usage.usage_available is True
    assert trace.token_usage.prompt_tokens == 230
    assert trace.token_usage.completion_tokens == 65
    assert trace.token_usage.total_tokens == 295
    assert created_children[0].captured_kwargs["metadata"]["input_tokens"] == 80
    assert created_children[1].captured_kwargs["usage_details"] == {
        "input": 150,
        "output": 45,
        "total": 195,
    }


def test_missing_usage_from_any_llm_stage_makes_query_total_unavailable():
    """Do not report a partial query token total when one LLM call omits usage."""
    mock_client, _, _ = _make_mock_langfuse()

    with patch("backend.app.tracing.tracer.get_langfuse_client", return_value=mock_client):
        tracer = PipelineTracer(trace_id="trace_unit_usage_partial")
        tracer.record_llm_usage(
            "openai/gpt-oss-20b", 80, 20, total_tokens=100,
            usage_available=True, stage="router",
        )
        tracer.record_llm_usage(
            "openai/gpt-oss-20b", None, None,
            usage_available=False, stage="generation",
        )
        trace = tracer.finalize()

    assert trace.token_usage.usage_available is False
    assert trace.token_usage.prompt_tokens is None
    assert trace.token_usage.completion_tokens is None
    assert trace.token_usage.total_tokens is None
    assert trace.estimated_cost_usd is None


def test_langfuse_redacts_sensitive_payloads_and_secrets():
    """Raw prompts, answers, doc text, auth headers, and secret tokens must never be sent to Langfuse."""
    mock_client, _, created_children = _make_mock_langfuse()

    with patch("backend.app.tracing.tracer.get_langfuse_client", return_value=mock_client):
        tracer = PipelineTracer(trace_id="trace_unit_003")
        tracer.record_span(
            "guardrail",
            1.0,
            details={
                "is_safe": True,
                "query": "My secret query",
                "prompt": "System prompt with context",
                "answer": "Full model answer",
                "document_text": "Private internal document text",
                "authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.secret",
                "api_key": "gsk_supersecretkey123456",
                "note": "Authorization header was Bearer abcdef12345 and key gsk_xyz987654",
            },
        )
        tracer.finalize()

    meta = created_children[0].captured_kwargs["metadata"]
    assert meta["is_safe"] is True
    for forbidden_key in ("query", "prompt", "answer", "document_text", "authorization", "api_key"):
        assert forbidden_key not in meta
    assert "abcdef12345" not in meta["note"]
    assert "gsk_xyz987654" not in meta["note"]
    assert "[REDACTED]" in meta["note"]


def test_langfuse_failure_does_not_break_request():
    """If Langfuse client or span calls raise exceptions, tracer degrades gracefully without raising."""
    broken_client = MagicMock()
    broken_client.create_trace_id.return_value = "b" * 32
    broken_root = MagicMock()
    broken_root.start_observation.side_effect = RuntimeError("Network timeout to Langfuse")
    broken_root.update.side_effect = RuntimeError("Network timeout")
    broken_client.start_observation.return_value = broken_root

    with patch("backend.app.tracing.tracer.get_langfuse_client", return_value=broken_client):
        tracer = PipelineTracer(trace_id="trace_unit_004")
        tracer.record_span("guardrail", 1.2, details={"is_safe": True})
        trace = tracer.finalize()

    assert trace.trace_id == "trace_unit_004"
    assert len(trace.spans) == 1
    assert trace.spans[0].stage == "guardrail"

    # Also test client.start_observation failing at init -> falls back to offline_mock
    broken_init_client = MagicMock()
    broken_init_client.create_trace_id.side_effect = RuntimeError("Auth failed")
    with patch("backend.app.tracing.tracer.get_langfuse_client", return_value=broken_init_client):
        tracer2 = PipelineTracer(trace_id="trace_unit_005")
        assert tracer2.langfuse_mode == "offline_mock"
        tracer2.record_span("router", 0.5)
        trace2 = tracer2.finalize()
        assert trace2.langfuse_mode == "offline_mock"
