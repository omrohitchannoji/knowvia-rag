"""
Retrieval & Generation Evaluation Metrics.
Implements Recall@K, MRR, NDCG@K, and Keyword Groundedness/Faithfulness metrics.
"""

import math
from typing import List, Union, Tuple, Optional

def _normalize_expected(expected: Union[str, List[str], None]) -> List[str]:
    if not expected:
        return []
    if isinstance(expected, str):
        return [expected.lower()]
    return [e.lower() for e in expected]

def calculate_recall_at_k(retrieved_docs: List[str], expected_docs: Union[str, List[str], None], k: int = 5) -> float:
    """
    Calculates Recall@K: Proportion of expected relevant documents present in the top-K retrieved list.
    """
    targets = _normalize_expected(expected_docs)
    if not targets:
        return 1.0  # For unanswerable queries with no expected target

    top_k = [doc.lower() for doc in retrieved_docs[:k]]
    hits = sum(1 for target in targets if any(target in doc for doc in top_k))
    return round(hits / len(targets), 4)

def calculate_mrr(retrieved_docs: List[str], expected_docs: Union[str, List[str], None]) -> float:
    """
    Calculates Mean Reciprocal Rank (MRR): 1 / rank of the first relevant document retrieved.
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
    Calculates Normalized Discounted Cumulative Gain (NDCG@K) for binary relevance.
    """
    targets = _normalize_expected(expected_docs)
    if not targets:
        return 1.0

    top_k = [doc.lower() for doc in retrieved_docs[:k]]
    
    # Calculate DCG
    dcg = 0.0
    for idx, doc in enumerate(top_k, start=1):
        rel = 1 if any(target in doc for target in targets) else 0
        dcg += rel / math.log2(idx + 1)

    # Calculate Ideal DCG (IDCG)
    idcg = 0.0
    for idx in range(1, min(len(targets), k) + 1):
        idcg += 1.0 / math.log2(idx + 1)

    if idcg == 0.0:
        return 0.0

    return round(dcg / idcg, 4)

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
    
    # Calculate keyword recall
    matched_keywords = sum(1 for kw in expected_keywords if kw.lower() in answer_lower)
    keyword_score = round(matched_keywords / len(expected_keywords), 4)

    # Safety check against prohibited strings
    is_safe = True
    if must_not_contain:
        for forbidden in must_not_contain:
            if forbidden.lower() in answer_lower:
                is_safe = False
                break

    return keyword_score, is_safe
