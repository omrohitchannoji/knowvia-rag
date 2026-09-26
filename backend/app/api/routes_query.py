import time
from fastapi import APIRouter, HTTPException, status
from backend.app.schemas.query import QueryRequest, QueryResponse, ChatMessage
from backend.app.security.input_guardrails import InputGuardrail
from backend.app.security.output_guardrails import OutputGuardrail
from backend.app.retrieval.hybrid import get_hybrid_retriever
from backend.app.retrieval.reranker import get_reranker
from backend.app.generation.service import get_generation_service
from backend.app.core.logging import logger

from backend.app.generation.intent_router import get_intent_router, QueryIntent, OUT_OF_SCOPE_RESPONSE
from backend.app.generation.contextualizer import QueryContextualizer

router = APIRouter(prefix="/query", tags=["RAG Question Answering"])

@router.post(
    "",
    response_model=QueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute RAG Question Answering Query",
    description="Full RAG Pipeline: Guardrails -> Intent Routing & Semantic Normalization -> Pre-Retrieval RBAC -> Hybrid Search -> Rerank -> LLM Generation."
)
def execute_query(req: QueryRequest):
    start_time = time.perf_counter()

    # 1. Input Guardrail Inspection (Prompt Injection & Jailbreak Defense)
    is_safe, violation_reason = InputGuardrail.inspect_query(req.query)
    if not is_safe:
        logger.warning(f"API Query Blocked by Input Guardrail: {violation_reason}")
        return QueryResponse(
            query=req.query,
            answer=f"I am unable to answer this request. {violation_reason}",
            citations=[],
            retrieved_chunks_count=0,
            is_abstained=True,
            latency_ms=0.0
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
    intent_router = get_intent_router()
    router_result = intent_router.route(clean_query, history_dicts)
    intent = router_result.intent

    # --- BRANCH A: CONVERSATIONAL ---
    if intent == QueryIntent.CONVERSATIONAL:
        logger.info(f"Query='{req.query}' | Intent=conversational | Retrieval=False")
        gen_service = get_generation_service()
        raw_answer = gen_service.generate_conversational(clean_query, history_dicts)
        redacted_answer, _ = OutputGuardrail.redact_secrets(raw_answer)
        latency = round((time.perf_counter() - start_time) * 1000, 2)
        return QueryResponse(
            query=req.query,
            answer=redacted_answer,
            citations=[],
            retrieved_chunks_count=0,
            is_abstained=False,
            latency_ms=latency
        )

    # --- BRANCH B: OUT OF SCOPE ---
    if intent == QueryIntent.OUT_OF_SCOPE:
        logger.info(f"Query='{req.query}' | Intent=out_of_scope | Retrieval=False")
        latency = round((time.perf_counter() - start_time) * 1000, 2)
        return QueryResponse(
            query=req.query,
            answer=OUT_OF_SCOPE_RESPONSE,
            citations=[],
            retrieved_chunks_count=0,
            is_abstained=False,
            latency_ms=latency
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
        # Hybrid Retrieval (Dense Vector + Sparse BM25 with Pre-Retrieval RBAC Authorization)
        hybrid_retriever = get_hybrid_retriever()
        hybrid_candidates = hybrid_retriever.retrieve(
            query=search_query,
            user_role=req.user_role,
            top_k=req.top_k or 5,
            filter_status=req.filter_status,
            filter_document_type=req.filter_document_type
        )

        # Cross-Encoder Joint-Attention Reranking
        reranker = get_reranker()
        reranked_candidates = reranker.rerank(
            query=search_query,
            candidates=hybrid_candidates,
            top_n=req.top_k or 5
        )

        # Grounded Generation Engine with Multi-Signal Evidence Assessment
        gen_service = get_generation_service()
        gen_response = gen_service.generate(
            query=clean_query,
            candidates=reranked_candidates,
            search_query=search_query,
            intent=intent.value
        )

        # Output Guardrail Secret & Credential Redaction
        redacted_answer, secrets_found = OutputGuardrail.redact_secrets(gen_response.answer)

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
            unsupported_aspects=gen_response.unsupported_aspects
        )

    except Exception as e:
        logger.error(f"Error during RAG query pipeline execution: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query execution failed: {str(e)}"
        )
