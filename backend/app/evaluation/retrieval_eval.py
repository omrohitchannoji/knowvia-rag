"""
Retrieval & Generation Evaluation Metrics.
Implements mathematically rigorous Recall@K, MRR, NDCG@K (bounded in [0, 1]),
Abstention Precision/Recall, Latency percentiles (p50/p95), and multi-dimensional Generation Quality metrics.
"""

import math
from typing import List, Dict, Any, Union, Tuple, Optional

def _normalize_expected(expected: Union[str, List[str], None]) -> List[str]:
    if not expected:
        return []
    if isinstance(expected, str):
        return [expected.lower().strip()]
    return [e.lower().strip() for e in expected if e and e.strip()]

def calculate_recall_at_k(retrieved_docs: List[str], expected_docs: Union[str, List[str], None], k: int = 5) -> float:
    """
    Calculates Recall@K: Proportion of expected relevant documents present in the top-K retrieved list.
    For unanswerable queries with no expected target, returns 1.0 (abstention target handled separately).
    """
    targets = _normalize_expected(expected_docs)
    if not targets:
        return 1.0

    top_k = [doc.lower() for doc in retrieved_docs[:k]]
    hits = sum(1 for target in targets if any(target in doc for doc in top_k))
    return round(hits / len(targets), 4)

def calculate_mrr(retrieved_docs: List[str], expected_docs: Union[str, List[str], None]) -> float:
    """
    Calculates Mean Reciprocal Rank (MRR): 1 / rank of the first relevant document retrieved.
    Returns 0.0 if no relevant target is found in retrieved candidates.
    """
    targets = _normalize_expected(expected_docs)
    if not targets:
        return 1.0

    for rank, doc in enumerate(retrieved_docs, start=1):
        doc_lower = doc.lower()
        if any(target in doc_lower for target in targets):
            return round(1.0 / rank, 4)
    return 0.0

def calculate_ndcg_at_k(retrieved_docs: List[str], expected_docs: Union[str, List[str], None], k: int = 5) -> float:
    """
    Calculates Normalized Discounted Cumulative Gain (NDCG@K) with deduplication per target.
    Guarantees mathematically valid output strictly bounded in [0.0, 1.0].
    """
    targets = _normalize_expected(expected_docs)
    if not targets:
        return 1.0

    top_k = [doc.lower() for doc in retrieved_docs[:k]]

    # Compute DCG with target deduplication (each expected target counts at most once)
    seen_targets = set()
    dcg = 0.0
    for idx, doc in enumerate(top_k, start=1):
        rel = 0
        for target in targets:
            if target in doc and target not in seen_targets:
                rel = 1
                seen_targets.add(target)
                break
        if rel > 0:
            dcg += rel / math.log2(idx + 1)

    # Compute Ideal DCG (IDCG) for the number of available targets up to k
    idcg = 0.0
    for idx in range(1, min(len(targets), k) + 1):
        idcg += 1.0 / math.log2(idx + 1)

    if idcg == 0.0:
        return 0.0

    score = dcg / idcg
    return round(min(1.0, max(0.0, score)), 4)

def calculate_percentile_latencies(latencies: List[float]) -> Dict[str, float]:
    """Computes p50 (median) and p95 latency percentiles from measured run latencies."""
    if not latencies:
        return {"p50_ms": 0.0, "p95_ms": 0.0, "mean_ms": 0.0}

    sorted_lats = sorted(latencies)
    n = len(sorted_lats)

    idx_p50 = int(round(0.50 * (n - 1)))
    idx_p95 = int(round(0.95 * (n - 1)))

    p50 = sorted_lats[idx_p50]
    p95 = sorted_lats[idx_p95]
    mean_val = sum(sorted_lats) / n

    return {
        "p50_ms": round(p50, 2),
        "p95_ms": round(p95, 2),
        "mean_ms": round(mean_val, 2)
    }

def calculate_abstention_metrics(
    predictions: List[bool],
    ground_truths: List[bool]
) -> Dict[str, float]:
    """
    Calculates Precision, Recall, and F1 for pipeline abstention.
    Positive class = Abstained (e.g., query was unanswerable/out_of_scope/forbidden).
    """
    if len(predictions) != len(ground_truths):
        raise ValueError("Mismatched counts for predictions and ground truths.")

    tp = sum(1 for p, g in zip(predictions, ground_truths) if p and g)
    fp = sum(1 for p, g in zip(predictions, ground_truths) if p and not g)
    fn = sum(1 for p, g in zip(predictions, ground_truths) if not p and g)
    tn = sum(1 for p, g in zip(predictions, ground_truths) if not p and not g)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "abstention_precision": round(precision, 4),
        "abstention_recall": round(recall, 4),
        "abstention_f1": round(f1, 4),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "true_negatives": tn
    }

def evaluate_generation_faithfulness(
    answer: str,
    expected_keywords: List[str],
    must_not_contain: Optional[List[str]] = None
) -> Tuple[float, bool]:
    """
    Evaluates LLM generation response:
    - Keyword Groundedness: Percentage of expected facts/keywords present in answer.
    - Safety Pass: True if answer contains no prohibited prompt injection / leak terms.
    """
    if not answer or not expected_keywords:
        return 0.0, True

    answer_lower = answer.lower()
    matched_keywords = sum(1 for kw in expected_keywords if kw.lower() in answer_lower)
    keyword_score = round(matched_keywords / len(expected_keywords), 4)

    is_safe = True
    if must_not_contain:
        for forbidden in must_not_contain:
            if forbidden.lower() in answer_lower:
                is_safe = False
                break

    return keyword_score, is_safe

def evaluate_generation_quality(
    query: str,
    answer: str,
    expected_keywords: List[str],
    expected_doc: Optional[str],
    citations: List[Any],
    is_abstained: bool,
    should_abstain: bool,
    must_not_contain: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Comprehensive multi-metric generation evaluation:
    1. Faithfulness / Groundedness: Fact/keyword presence and lack of prohibited tokens.
    2. Answer Relevance: Topic coverage relative to expected keywords.
    3. Citation Correctness: Citations align with expected document source and contain valid citation blocks.
    4. Appropriate Abstention: Correctness of abstention decision.
    """
    if should_abstain:
        appropriate_abstention = 1.0 if is_abstained else 0.0
        faithfulness = 1.0 if is_abstained else 0.0
        relevance = 1.0 if is_abstained else 0.0
        citation_correctness = 1.0 if (is_abstained and len(citations) == 0) else 0.0
    else:
        appropriate_abstention = 1.0 if not is_abstained else 0.0
        kw_score, is_safe = evaluate_generation_faithfulness(answer, expected_keywords, must_not_contain)
        faithfulness = kw_score if is_safe else 0.0
        relevance = kw_score

        # Citation evaluation
        if not citations:
            citation_correctness = 0.0
        else:
            # Check if at least one citation matches expected document
            doc_target = expected_doc.lower() if expected_doc else ""
            matches = 0
            for c in citations:
                doc_name = getattr(c, "document_name", "") or (c.get("document_name", "") if isinstance(c, dict) else "")
                section = getattr(c, "section", "") or (c.get("section", "") if isinstance(c, dict) else "")
                combined = f"{doc_name} {section}".lower()
                if doc_target in combined:
                    matches += 1
            citation_correctness = round(min(1.0, matches / max(1, len(citations))), 4) if doc_target else 1.0

    return {
        "faithfulness": round(faithfulness, 4),
        "relevance": round(relevance, 4),
        "citation_correctness": round(citation_correctness, 4),
        "appropriate_abstention": round(appropriate_abstention, 4)
    }
