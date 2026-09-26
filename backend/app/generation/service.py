import time
import re
from typing import List, Dict, Any, Optional
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.schemas.query import QueryResponse, Citation
from backend.app.generation.context import ContextBuilder
from backend.app.generation.prompts import SYSTEM_GROUNDING_PROMPT, SYSTEM_CONVERSATIONAL_PROMPT, build_user_prompt
from backend.app.generation.llm import get_llm_client, BaseLLMClient
from backend.app.answerability.evaluator import get_evidence_evaluator
from backend.app.answerability.models import EvidenceStatus

ABSTAIN_TEXT = "I am unable to answer based on the provided context."

class GenerationService:
    def __init__(self, llm_client: Optional[BaseLLMClient] = None):
        self.llm_client = llm_client or get_llm_client()
        self.evidence_evaluator = get_evidence_evaluator()

    def generate_conversational(
        self,
        query: str,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Generates a natural conversational response for greetings, identity, and capability queries using LLM.
        Bypasses document retrieval, vector DB, reranker, and RAG grounding/abstention completely.
        """
        history_str = ""
        if chat_history:
            formatted_turns = [f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in chat_history[-5:]]
            history_str = "\n".join(formatted_turns)

        user_prompt = f"USER MESSAGE: {query}"
        if history_str:
            user_prompt = f"CONVERSATION HISTORY:\n{history_str}\n\n{user_prompt}"

        try:
            return self.llm_client.generate(
                system_prompt=SYSTEM_CONVERSATIONAL_PROMPT,
                user_prompt=user_prompt,
                temperature=0.3
            )
        except Exception as e:
            logger.error(f"Error in conversational LLM generation: {e}")
            return (
                "Hello! I am the Technical Documentation Intelligence Assistant. "
                "I am designed to help you search, analyze, and understand technical documentation, "
                "Kubernetes Jobs, CronJobs, Pod Autoscaling (HPA), Databricks job management, "
                "parallel work queues, and cloud/container infrastructure."
            )

    def generate(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        search_query: Optional[str] = None,
        intent: str = "knowledge"
    ) -> QueryResponse:
        """
        Executes end-to-end RAG Generation Pipeline with Evidence Assessment:
        1. Multi-signal Evidence Assessment (STRONG, PARTIAL, INSUFFICIENT).
        2. Formats tagged context blocks and maps citations.
        3. Constructs prompt injection resistant user prompt with coverage directives.
        4. Invokes LLM Provider.
        5. Extracts inline citations and returns structured response with latency.
        """
        start_time = time.perf_counter()
        effective_search_q = search_query or query

        # 1. Multi-Signal Evidence & Answerability Assessment
        assessment = self.evidence_evaluator.assess(
            query=query,
            search_query=effective_search_q,
            intent=intent,
            candidates=candidates
        )

        logger.info(
            f"Evidence Assessment: Status={assessment.status.value} | "
            f"Score={assessment.evidence_score:.4f} | Signal={assessment.confidence_signal:.4f} | "
            f"Raw={assessment.raw_score:.2f} | Supported={assessment.supported_aspects} | "
            f"Unsupported={assessment.unsupported_aspects} | Reason={assessment.reason}"
        )

        # 2. Handle INSUFFICIENT Evidence State
        if assessment.status == EvidenceStatus.INSUFFICIENT:
            latency = round((time.perf_counter() - start_time) * 1000, 2)
            return QueryResponse(
                query=query,
                answer=ABSTAIN_TEXT,
                citations=[],
                retrieved_chunks_count=len(candidates),
                is_abstained=True,
                latency_ms=latency,
                evidence_status=assessment.status.value,
                supported_aspects=assessment.supported_aspects,
                unsupported_aspects=assessment.unsupported_aspects
            )

        # 3. Assemble Context & Citation Mappings for STRONG or PARTIAL states
        # Filter candidate context to top supporting candidates
        eval_candidates = candidates[:settings.RERANK_TOP_N]
        formatted_context, citations = ContextBuilder.format_context(eval_candidates)

        # 4. Construct Security-Hardened User Prompt
        user_prompt = build_user_prompt(
            query=query,
            formatted_context=formatted_context,
            evidence_status=assessment.status.value,
            supported_aspects=", ".join(assessment.supported_aspects),
            unsupported_aspects=", ".join(assessment.unsupported_aspects)
        )

        # 5. Invoke LLM Client
        try:
            raw_answer = self.llm_client.generate(
                system_prompt=SYSTEM_GROUNDING_PROMPT,
                user_prompt=user_prompt,
                temperature=settings.LLM_TEMPERATURE
            )
        except Exception as e:
            logger.error(f"Generation error during LLM invocation: {e}")
            raw_answer = ABSTAIN_TEXT

        # 6. Post-Process Abstention Detection & Citation Validation
        is_abstained = False
        if ABSTAIN_TEXT.lower() in raw_answer.lower():
            is_abstained = True
            used_citations = []
        else:
            referenced_indices = set(map(int, re.findall(r"\[Source (\d+)\]", raw_answer)))
            if referenced_indices:
                used_citations = [c for c in citations if c.source_index in referenced_indices]
            else:
                used_citations = citations

        latency = round((time.perf_counter() - start_time) * 1000, 2)

        return QueryResponse(
            query=query,
            answer=raw_answer,
            citations=used_citations,
            retrieved_chunks_count=len(candidates),
            is_abstained=is_abstained,
            latency_ms=latency,
            evidence_status=assessment.status.value,
            supported_aspects=assessment.supported_aspects,
            unsupported_aspects=assessment.unsupported_aspects
        )

# Singleton helper
_generation_service = None

def get_generation_service() -> GenerationService:
    global _generation_service
    if _generation_service is None:
        _generation_service = GenerationService()
    return _generation_service
