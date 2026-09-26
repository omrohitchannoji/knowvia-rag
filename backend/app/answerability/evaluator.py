import re
from typing import List, Dict, Any, Optional, Tuple
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.answerability.models import EvidenceStatus, EvidenceAssessmentResult

COMMON_ASPECT_MAP = {
    "best practices": ["job management", "automation", "API & SDK usage", "CI/CD integration", "infrastructure as code", "cluster sizing", "cost optimization", "security governance"],
    "best practice": ["job management", "automation", "API & SDK usage", "CI/CD integration", "infrastructure as code", "cluster sizing", "cost optimization", "security governance"],
    "optimization": ["performance tuning", "resource allocation", "autoscaling", "cost reduction"],
    "security": ["authentication", "OAuth2 & bearer tokens", "RBAC access control", "secret management", "encryption"],
    "troubleshooting": ["error codes", "logs inspection", "pod status monitoring", "retry policies"],
    "configuration": ["YAML specifications", "environment variables", "parameters", "concurrency rules"]
}

class EvidenceEvaluator:
    def __init__(
        self,
        strong_threshold: Optional[float] = None,
        partial_threshold: Optional[float] = None
    ):
        self.strong_threshold = strong_threshold if strong_threshold is not None else getattr(settings, "ANSWERABILITY_STRONG_THRESHOLD", 0.65)
        self.partial_threshold = partial_threshold if partial_threshold is not None else getattr(settings, "ANSWERABILITY_PARTIAL_THRESHOLD", 0.20)

    def assess(
        self,
        query: str,
        search_query: str,
        intent: str,
        candidates: List[Dict[str, Any]]
    ) -> EvidenceAssessmentResult:
        """
        Multi-Signal Evidence & Answerability Assessment Engine.
        Evaluates Reranker Logits, TrueData Metadata, Aspect Coverage, and Retrieval Agreement.
        Returns EvidenceAssessmentResult (STRONG, PARTIAL, INSUFFICIENT).
        """
        if not candidates:
            return EvidenceAssessmentResult(
                status=EvidenceStatus.INSUFFICIENT,
                confidence_signal=0.0,
                raw_score=-99.0,
                evidence_score=0.0,
                supported_aspects=[],
                unsupported_aspects=[],
                supporting_documents=[],
                reason="No retrieved candidate chunks."
            )

        # 1. Extract Reranker Signals
        top_cand = candidates[0]
        prob_score = top_cand.get("rerank_score", top_cand.get("hybrid_score", top_cand.get("score", 0.0)))
        raw_score = top_cand.get("raw_rerank_score", 0.0)

        # 2. Filter & Audit TrueData vs NoisyData Candidates
        true_data_cands = []
        noisy_data_cands = []

        for cand in candidates:
            payload = cand.get("payload", {})
            cat = cand.get("data_category") or payload.get("data_category", "true")
            if cat == "true":
                true_data_cands.append(cand)
            else:
                noisy_data_cands.append(cand)

        # Use TrueData top candidate if available; fallback to overall top candidate
        target_cand = true_data_cands[0] if true_data_cands else top_cand
        target_prob = target_cand.get("rerank_score", prob_score)
        target_raw = target_cand.get("raw_rerank_score", raw_score)

        # 3. Dense & BM25 Agreement Signal
        agreement_count = sum(
            1 for c in candidates 
            if c.get("dense_rank") is not None and c.get("bm25_rank") is not None
        )

        # 4. Aspect Coverage Analysis
        supported_aspects, unsupported_aspects = self._analyze_aspect_coverage(query, search_query, true_data_cands or candidates)

        # 5. Calculate Combined Multi-Signal Evidence Score
        base_signal = max(target_prob, 0.0)
        agreement_bonus = 0.10 if agreement_count > 0 else 0.0
        coverage_bonus = 0.10 if len(supported_aspects) > 0 else 0.0
        noisy_penalty = 0.15 if not true_data_cands and noisy_data_cands else 0.0

        evidence_score = round(min(max(base_signal + agreement_bonus + coverage_bonus - noisy_penalty, 0.0), 1.0), 4)

        # Extract supporting document metadata
        valid_supporting_docs = [
            {
                "chunk_id": c.get("chunk_id"),
                "document_name": c.get("document_name") or c.get("payload", {}).get("document_name"),
                "section": c.get("payload", {}).get("section_title") or c.get("payload", {}).get("section", "General"),
                "data_category": c.get("payload", {}).get("data_category", "true"),
                "rerank_score": c.get("rerank_score")
            }
            for c in (true_data_cands or candidates)[:3]
        ]

        # 6. Status Determination Matrix
        if target_raw < -3.5 or target_prob < self.partial_threshold:
            # Low relevance or raw logit < -3.5 -> INSUFFICIENT
            if not true_data_cands and noisy_data_cands:
                reason = f"Top candidate is NoisyData distractor with raw logit {target_raw:.2f} (prob {target_prob:.4f})."
            else:
                reason = f"Reranker relevance signal low (raw logit {target_raw:.2f}, prob {target_prob:.4f} < threshold {self.partial_threshold})."
            
            return EvidenceAssessmentResult(
                status=EvidenceStatus.INSUFFICIENT,
                confidence_signal=target_prob,
                raw_score=target_raw,
                evidence_score=evidence_score,
                supported_aspects=supported_aspects,
                unsupported_aspects=unsupported_aspects,
                supporting_documents=[],
                reason=reason
            )

        if target_raw >= 1.0 or target_prob >= self.strong_threshold:
            if unsupported_aspects and len(unsupported_aspects) > len(supported_aspects):
                # Strong score but missing significant aspects -> PARTIAL
                reason = f"High relevance signal (raw logit {target_raw:.2f}), but query requests broad aspects not fully covered."
                return EvidenceAssessmentResult(
                    status=EvidenceStatus.PARTIAL,
                    confidence_signal=target_prob,
                    raw_score=target_raw,
                    evidence_score=evidence_score,
                    supported_aspects=supported_aspects,
                    unsupported_aspects=unsupported_aspects,
                    supporting_documents=valid_supporting_docs,
                    reason=reason
                )
            else:
                # High score and good coverage -> STRONG
                reason = f"Strong evidence signal (raw logit {target_raw:.2f}, prob {target_prob:.4f} >= {self.strong_threshold}) with TrueData support."
                return EvidenceAssessmentResult(
                    status=EvidenceStatus.STRONG,
                    confidence_signal=target_prob,
                    raw_score=target_raw,
                    evidence_score=evidence_score,
                    supported_aspects=supported_aspects,
                    unsupported_aspects=unsupported_aspects,
                    supporting_documents=valid_supporting_docs,
                    reason=reason
                )

        # Reranker score is in moderate partial range [0.20, 0.65) -> PARTIAL
        reason = f"Moderate evidence signal (raw logit {target_raw:.2f}, prob {target_prob:.4f} in PARTIAL range [{self.partial_threshold}, {self.strong_threshold}))."
        return EvidenceAssessmentResult(
            status=EvidenceStatus.PARTIAL,
            confidence_signal=target_prob,
            raw_score=target_raw,
            evidence_score=evidence_score,
            supported_aspects=supported_aspects,
            unsupported_aspects=unsupported_aspects,
            supporting_documents=valid_supporting_docs,
            reason=reason
        )

    def _analyze_aspect_coverage(
        self,
        query: str,
        search_query: str,
        candidates: List[Dict[str, Any]]
    ) -> Tuple[List[str], List[str]]:
        """
        Lightweight deterministic aspect coverage analysis matching query concepts against retrieved chunks.
        """
        q_lower = (query + " " + search_query).lower()
        combined_text = " ".join([c.get("text", "") for c in candidates]).lower()

        matched_key = None
        for key in COMMON_ASPECT_MAP:
            if key in q_lower:
                matched_key = key
                break

        if not matched_key:
            return [], []

        all_potential_aspects = COMMON_ASPECT_MAP[matched_key]
        supported = []
        unsupported = []

        for aspect in all_potential_aspects:
            aspect_terms = re.findall(r"\w+", aspect.lower())
            if any(term in combined_text for term in aspect_terms if len(term) > 3):
                supported.append(aspect)
            else:
                unsupported.append(aspect)

        return supported, unsupported

# Singleton helper
_evaluator_instance = None

def get_evidence_evaluator() -> EvidenceEvaluator:
    global _evaluator_instance
    if _evaluator_instance is None:
        _evaluator_instance = EvidenceEvaluator()
    return _evaluator_instance
