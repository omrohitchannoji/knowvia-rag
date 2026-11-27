import time
import uuid
from typing import Any, Dict
from fastapi import APIRouter, HTTPException, status, Depends
from backend.app.security.auth import get_current_user
from backend.app.schemas.query import QueryRequest, QueryResponse, ChatMessage
from backend.app.security.input_guardrails import InputGuardrail
from backend.app.security.output_guardrails import OutputGuardrail
from backend.app.retrieval.hybrid import get_hybrid_retriever
from backend.app.retrieval.reranker import get_reranker
from backend.app.generation.service import get_generation_service
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.tracing.tracer import PipelineTracer

from backend.app.generation.intent_router import get_intent_router, QueryIntent, OUT_OF_SCOPE_RESPONSE
from backend.app.generation.contextualizer import QueryContextualizer

router = APIRouter(prefix="/query", tags=["RAG Question Answering"])


def _record_usage(tracer: PipelineTracer, usage: Dict[str, Any], stage: str) -> None:
    usage_avail = bool(usage.get("usage_available", False))
    p_tok = usage.get("prompt_tokens") if usage_avail else None
    c_tok = usage.get("completion_tokens") if usage_avail else None
    t_tok = usage.get("total_tokens") if usage_avail else None
    tracer.record_llm_usage(
        str(usage.get("model", settings.LLM_MODEL) or settings.LLM_MODEL),
        int(p_tok) if isinstance(p_tok, (int, float)) else None,
        int(c_tok) if isinstance(c_tok, (int, float)) else None,
        total_tokens=int(t_tok) if isinstance(t_tok, (int, float)) else None,
        usage_available=usage_avail,
        stage=stage,
    )


def _record_client_usage(tracer: PipelineTracer, gen_service) -> None:
    # Read only usage captured by this specific generation call. If evidence
    # assessment abstained before calling the model, don't reuse router/stale usage.
    usage = getattr(gen_service, "last_call_usage", None)
    if isinstance(usage, dict):
        _record_usage(tracer, usage, stage="generation")

@router.post(
    "",
    response_model=QueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute RAG Question Answering Query",
    description="Full RAG Pipeline with Pre-Retrieval Authorization, Hybrid Retrieval, Reranking, Guardrails, and Tracing."
)
def execute_query(req: QueryRequest, user: dict = Depends(get_current_user)):
    start_time = time.perf_counter()
    tracer = PipelineTracer(trace_id=f"tr_{uuid.uuid4().hex[:12]}")

    # Security check: User role is strictly bound to verified identity
    verified_role = user.get("role", "PUBLIC_USER")
    if req.user_role and req.user_role.upper() != verified_role:
        logger.warning(
            f"Audit Notice: Caller sent body user_role='{req.user_role}', "
            f"but authenticated identity has role='{verified_role}'. Enforcing verified role strictly."
        )

    # 1. Input Guardrail Inspection (Prompt Injection & Jailbreak Defense)
    t_guard = time.perf_counter()
    is_safe, violation_reason = InputGuardrail.inspect_query(req.query)
    tracer.record_span(
        "guardrail",
        (time.perf_counter() - t_guard) * 1000,
        status="ok" if is_safe else "blocked",
        details={"is_safe": is_safe, "violation": violation_reason if not is_safe else None}
    )

    if not is_safe:
        logger.warning(f"API Query Blocked by Input Guardrail: {violation_reason}")
        final_trace = tracer.finalize()
        return QueryResponse(
            query=req.query,
            answer=f"I am unable to answer this request. {violation_reason}",
            citations=[],
            retrieved_chunks_count=0,
            is_abstained=True,
            latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
            trace=final_trace.model_dump(),
            token_usage=final_trace.token_usage.model_dump(),
            estimated_cost_usd=final_trace.estimated_cost_usd
        )

    # Sanitize Query Text
    clean_query = InputGuardrail.sanitize_query(req.query)

    # Convert Chat History to dict format for Router/Contextualizer/LLM
    history_dicts = []
    if req.chat_history:
        for item in req.chat_history:
            if isinstance(item, ChatMessage):
                history_dicts.append({"role": item.role, "content": item.content})
            elif isinstance(item, dict):
                history_dicts.append({"role": item.get("role", "user"), "content": item.get("content", "")})

    # 2. Dynamic 2-Tier Intent Router & Semantic Classifier
    t_router = time.perf_counter()
    intent_router = get_intent_router()
    router_usage: Dict[str, Any] = {}

    def capture_router_usage(usage: Dict[str, Any]) -> None:
        router_usage.update(usage)
        _record_usage(tracer, usage, stage="router")

    router_result = intent_router.route(
        clean_query,
        history_dicts,
        usage_callback=capture_router_usage,
    )
    intent = router_result.intent
    router_details: Dict[str, Any] = {"intent": intent.value}
    if router_usage:
        router_details["token_usage_available"] = bool(router_usage.get("usage_available", False))
        if router_usage.get("usage_available"):
            router_details.update({
                "input_tokens": router_usage.get("prompt_tokens"),
                "output_tokens": router_usage.get("completion_tokens"),
                "total_tokens": router_usage.get("total_tokens"),
            })
    tracer.record_span(
        "router",
        (time.perf_counter() - t_router) * 1000,
        details=router_details
    )

    # --- BRANCH A: CONVERSATIONAL ---
    if intent == QueryIntent.CONVERSATIONAL:
        logger.info(f"Query='{req.query}' | Intent=conversational | Retrieval=False")
        t_gen = time.perf_counter()
        gen_service = get_generation_service()
        raw_answer = gen_service.generate_conversational(clean_query, history_dicts)
        _record_client_usage(tracer, gen_service)
        tracer.record_span("generation", (time.perf_counter() - t_gen) * 1000, details={"intent": "conversational"})

        redacted_answer, _ = OutputGuardrail.redact_secrets(raw_answer)
        final_trace = tracer.finalize()
        latency = round((time.perf_counter() - start_time) * 1000, 2)
        return QueryResponse(
            query=req.query,
            answer=redacted_answer,
            citations=[],
            retrieved_chunks_count=0,
            is_abstained=False,
            latency_ms=latency,
            trace=final_trace.model_dump(),
            token_usage=final_trace.token_usage.model_dump(),
            estimated_cost_usd=final_trace.estimated_cost_usd
        )

    # --- BRANCH B: OUT OF SCOPE ---
    if intent == QueryIntent.OUT_OF_SCOPE:
        logger.info(f"Query='{req.query}' | Intent=out_of_scope | Retrieval=False")
        final_trace = tracer.finalize()
        latency = round((time.perf_counter() - start_time) * 1000, 2)
        return QueryResponse(
            query=req.query,
            answer=OUT_OF_SCOPE_RESPONSE,
            citations=[],
            retrieved_chunks_count=0,
            is_abstained=False,
            latency_ms=latency,
            trace=final_trace.model_dump(),
            token_usage=final_trace.token_usage.model_dump(),
            estimated_cost_usd=final_trace.estimated_cost_usd
        )

    # --- BRANCH C: HYBRID or KNOWLEDGE (RAG EXECUTION) ---
    is_hybrid = (intent == QueryIntent.HYBRID)
    if is_hybrid:
        if router_result.search_query and router_result.search_query.strip():
            search_query = router_result.search_query.strip()
        else:
            search_query = QueryContextualizer.contextualize_query(clean_query, history_dicts)
        logger.info(f"Query='{req.query}' | Intent=hybrid | Retrieval=True | Contextualized=True | SearchQuery='{search_query}'")
    else:
        search_query = router_result.search_query.strip() if (router_result.search_query and router_result.search_query.strip()) else clean_query
        logger.info(f"Query='{req.query}' | Intent=knowledge | Retrieval=True | Contextualized=False")

    try:
        # 3. Pre-Retrieval Authorized Hybrid Search (Dense + BM25 + Fusion)
        hybrid_retriever = get_hybrid_retriever()
        try:
            fused_candidates = hybrid_retriever.retrieve(
                query=search_query,
                user_role=verified_role,
                top_k=(req.top_k or settings.TOP_K_DENSE) * 2,
                filter_status=req.filter_status,
                filter_document_type=req.filter_document_type,
                tracer=tracer
            )
        except TypeError:
            fused_candidates = hybrid_retriever.retrieve(
                query=search_query,
                user_role=verified_role,
                top_k=(req.top_k or settings.TOP_K_DENSE) * 2,
                filter_status=req.filter_status,
                filter_document_type=req.filter_document_type
            )
        if not isinstance(fused_candidates, list):
            fused_candidates = []

        # 4. Cross-Encoder Joint-Attention Reranking Span
        t_rerank = time.perf_counter()
        reranker = get_reranker()
        reranked_candidates = reranker.rerank(
            query=search_query,
            candidates=fused_candidates,
            top_n=req.top_k or 5
        )
        if not isinstance(reranked_candidates, list):
            reranked_candidates = []
        tracer.record_span(
            "reranking",
            (time.perf_counter() - t_rerank) * 1000,
            details={"top_n": req.top_k or 5, "candidates_reranked": len(reranked_candidates)}
        )

        # 5. Grounded Generation Engine Span
        t_gen = time.perf_counter()
        gen_service = get_generation_service()
        gen_response = gen_service.generate(
            query=clean_query,
            candidates=reranked_candidates,
            search_query=search_query,
            intent=intent.value
        )
        _record_client_usage(tracer, gen_service)
        tracer.record_span(
            "generation",
            (time.perf_counter() - t_gen) * 1000,
            details={
                "evidence_status": gen_response.evidence_status,
                "is_abstained": gen_response.is_abstained,
                "citations_count": len(gen_response.citations)
            }
        )

        # Output Guardrail Secret & Credential Redaction
        redacted_answer, secrets_found = OutputGuardrail.redact_secrets(gen_response.answer)

        final_trace = tracer.finalize()
        latency = round((time.perf_counter() - start_time) * 1000, 2)

        return QueryResponse(
            query=req.query,
            answer=redacted_answer,
            citations=gen_response.citations,
            retrieved_chunks_count=gen_response.retrieved_chunks_count,
            is_abstained=gen_response.is_abstained,
            latency_ms=latency,
            evidence_status=gen_response.evidence_status,
            supported_aspects=gen_response.supported_aspects,
            unsupported_aspects=gen_response.unsupported_aspects,
            trace=final_trace.model_dump(),
            token_usage=final_trace.token_usage.model_dump(),
            estimated_cost_usd=final_trace.estimated_cost_usd
        )

    except Exception as e:
        tracer.record_span(
            "generation",
            0.0,
            status="error",
            details={"error_type": type(e).__name__}
        )
        tracer.finalize()
        logger.error(f"Error during RAG query pipeline execution: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query execution failed: {str(e)}"
        )
