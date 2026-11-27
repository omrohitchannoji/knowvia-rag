"""
Regression tests for observed evaluation failures and K-4 tracing/cost requirements:
1. Out-of-scope questions must NOT route to conversational handling.
2. Unanswerable etcd secret-key query must still abstain even with technical keyword overlap.
3. Valid technical HPA question with grounded chunk must not be falsely rejected.
4. Tracing redacts payloads/secrets and marks unset pricing/missing tokens as unavailable.
"""

from unittest.mock import MagicMock
from backend.app.generation.intent_router import IntentRouter, QueryIntent
from backend.app.answerability.evaluator import EvidenceEvaluator
from backend.app.answerability.models import EvidenceStatus
from backend.app.tracing.tracer import PipelineTracer, calculate_cost
from backend.app.core.config import settings


def test_out_of_scope_does_not_route_to_conversational():
    """Out-of-scope questions must route to OUT_OF_SCOPE even when Tier 2 LLM falls back."""
    mock_llm = MagicMock()
    mock_llm.generate.return_value = "Non-JSON fallback text"
    router = IntentRouter(llm_client=mock_llm)

    for q in [
        "What is the capital city of France?",
        "Can you recommend a good stock to buy on the NASDAQ today?",
        "How many interstellar probes did NASA launch to Alpha Centauri last month?",
        "What is the best recipe for baking chocolate chip cookies?",
    ]:
        res = router.route(q)
        assert res.intent == QueryIntent.OUT_OF_SCOPE, f"Query '{q}' routed to {res.intent} instead of OUT_OF_SCOPE"


def test_greetings_still_route_to_conversational():
    """Legitimate greetings and identity questions still route to CONVERSATIONAL."""
    mock_llm = MagicMock()
    mock_llm.generate.return_value = "Non-JSON fallback text"
    router = IntentRouter(llm_client=mock_llm)

    for q in ["Hello!", "Who are you?", "Thanks for the explanation!"]:
        res = router.route(q)
        assert res.intent == QueryIntent.CONVERSATIONAL, f"Greeting '{q}' routed to {res.intent}"


def test_etcd_secret_key_must_abstain_despite_keyword_overlap():
    """
    Unanswerable etcd secret-key query contains technical terms ('Kubernetes', 'etcd')
    but lacks answerable evidence and MUST still abstain (INSUFFICIENT).
    """
    evaluator = EvidenceEvaluator(strong_threshold=0.65, partial_threshold=0.20)
    query = "What is the secret decryption key for the Kubernetes control plane etcd database?"

    # Simulate candidate chunks that share Kubernetes/etcd keywords but do NOT have strong evidence
    candidates = [
        {
            "chunk_id": "k8s_1",
            "document_name": "Kubernetes Architecture",
            "text": "The Kubernetes control plane uses etcd as its consistent backing store for cluster data.",
            "rerank_score": 0.42,  # Above partial_threshold=0.20, below strong_threshold=0.65
            "raw_rerank_score": -0.32,
            "bm25_rank": 1,
            "dense_rank": 1,
            "payload": {"data_category": "true", "document_name": "Kubernetes Architecture"}
        }
    ]
    result = evaluator.assess(query=query, search_query=query, intent="knowledge", candidates=candidates)
    assert result.status == EvidenceStatus.INSUFFICIENT


def test_valid_technical_query_with_strong_chunk_not_falsely_rejected():
    """Valid technical HPA question with a high-relevance HPA chunk must NOT abstain."""
    evaluator = EvidenceEvaluator(strong_threshold=0.65, partial_threshold=0.20)
    query = "How does HPA calculate the desired number of replicas from current metrics?"
    candidates = [
        {
            "chunk_id": "hpa_1",
            "document_name": "pods_autoscale.html",
            "text": "HPA calculates desiredReplicas = ceil[currentReplicas * (currentMetricValue / desiredMetricValue)].",
            "rerank_score": 0.88,
            "raw_rerank_score": 2.0,
            "bm25_rank": 1,
            "dense_rank": 1,
            "payload": {"data_category": "true", "document_name": "pods_autoscale.html"}
        }
    ]
    result = evaluator.assess(query=query, search_query=query, intent="knowledge", candidates=candidates)
    assert result.status in (EvidenceStatus.STRONG, EvidenceStatus.PARTIAL)


def test_tracer_redaction_and_unavailable_tokens_and_cost():
    """
    Verifies K-4:
    - Traces strip raw prompts, queries, document text, and secrets by default.
    - Missing provider token usage is marked unavailable (None), never estimated.
    - Unset MODEL_PRICING rates report cost as unavailable (None), never invented.
    """
    tracer = PipelineTracer(trace_id="test_trace_k4")
    tracer.record_span(
        "guardrail",
        1.5,
        details={
            "is_safe": True,
            "query": "sensitive user query",
            "prompt": "system prompt secret",
            "document_text": "confidential doc body",
            "api_key": "sk-secret-123"
        }
    )
    tracer.record_llm_usage(
        model_name=settings.LLM_MODEL,
        prompt_tokens=None,
        completion_tokens=None,
        usage_available=False
    )
    trace = tracer.finalize()

    span_details = trace.spans[0].details
    assert span_details.get("is_safe") is True
    assert "query" not in span_details
    assert "prompt" not in span_details
    assert "document_text" not in span_details
    assert "api_key" not in span_details

    assert trace.token_usage.usage_available is False
    assert trace.token_usage.prompt_tokens is None
    assert trace.token_usage.total_tokens is None
    assert trace.estimated_cost_usd is None
    assert trace.cost_calculation_details.get("cost_available") is False

    # Even with token counts present, unset pricing rates must return None (unavailable)
    cost, details = calculate_cost("openai/gpt-oss-20b", prompt_tokens=500, completion_tokens=100, usage_available=True)
    assert cost is None
    assert details.get("cost_available") is False
