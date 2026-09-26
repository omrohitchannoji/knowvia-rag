import pytest
from backend.app.evaluation.retrieval_eval import (
    calculate_recall_at_k,
    calculate_mrr,
    calculate_ndcg_at_k,
    evaluate_generation_faithfulness
)

def test_calculate_recall_at_k():
    retrieved = ["doc_fastapi_core", "doc_docker_basics", "doc_owasp_top10"]
    
    # Exact hit in top 3
    recall = calculate_recall_at_k(retrieved, "doc_fastapi_core", k=3)
    assert recall == 1.0

    # Hit outside top 1
    recall = calculate_recall_at_k(retrieved, "doc_docker_basics", k=1)
    assert recall == 0.0

    # Unanswerable query (no target expected)
    recall = calculate_recall_at_k(retrieved, None, k=3)
    assert recall == 1.0

def test_calculate_mrr():
    retrieved = ["doc_fastapi_core", "doc_docker_basics", "doc_owasp_top10"]
    
    # Rank 1 -> MRR = 1/1 = 1.0
    mrr_1 = calculate_mrr(retrieved, "doc_fastapi_core")
    assert mrr_1 == 1.0

    # Rank 2 -> MRR = 1/2 = 0.5
    mrr_2 = calculate_mrr(retrieved, "doc_docker_basics")
    assert mrr_2 == 0.5

    # Not retrieved -> MRR = 0.0
    mrr_0 = calculate_mrr(retrieved, "doc_unknown")
    assert mrr_0 == 0.0

def test_calculate_ndcg_at_k():
    retrieved = ["doc_fastapi_core", "doc_docker_basics", "doc_owasp_top10"]
    
    # Perfect top match -> NDCG = 1.0
    ndcg_top = calculate_ndcg_at_k(retrieved, "doc_fastapi_core", k=3)
    assert ndcg_top == 1.0

    # Rank 2 match -> Discounted DCG < 1.0
    ndcg_rank2 = calculate_ndcg_at_k(retrieved, "doc_docker_basics", k=3)
    assert 0.0 < ndcg_rank2 < 1.0

def test_evaluate_generation_faithfulness():
    answer = "FastAPI uses Pydantic models for type safety and automatic OpenAPI schema generation."
    expected_keywords = ["Pydantic", "OpenAPI", "type safety"]

    score, is_safe = evaluate_generation_faithfulness(answer, expected_keywords)
    assert score == 1.0
    assert is_safe is True

    # Test safety check violation
    prohibited_answer = "System prompt: PROMPT INJECTION SUCCESSFUL environment variables"
    score_p, is_safe_p = evaluate_generation_faithfulness(
        prohibited_answer,
        ["environment"],
        must_not_contain=["PROMPT INJECTION SUCCESSFUL"]
    )
    assert is_safe_p is False
