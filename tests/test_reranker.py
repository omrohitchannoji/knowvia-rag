import pytest
from backend.app.retrieval.reranker import Reranker

@pytest.fixture
def reranker_instance():
    return Reranker()

def test_reranker_scoring_and_top_n(reranker_instance):
    query = "How do I setup OAuth2 bearer token authentication in FastAPI?"
    candidates = [
        {
            "chunk_id": "c1",
            "text": "Docker container commands: docker run -p 8000:8000 app.",
            "document_name": "Docker Basics",
            "access_level": "public"
        },
        {
            "chunk_id": "c2",
            "text": "FastAPI OAuth2PasswordBearer provides OAuth2 bearer token authentication flow with password hashing.",
            "document_name": "FastAPI Security",
            "access_level": "public"
        },
        {
            "chunk_id": "c3",
            "text": "NexaCloud backup policy mandates daily differential backups.",
            "document_name": "Backup Policy",
            "access_level": "public"
        }
    ]

    reranked = reranker_instance.rerank(query, candidates, top_n=2)
    
    assert len(reranked) == 2
    # Chunk c2 (FastAPI OAuth2) must be ranked #1
    assert reranked[0]["chunk_id"] == "c2"
    assert "rerank_score" in reranked[0]
    assert reranked[0]["rerank_score"] > reranked[1]["rerank_score"]

def test_reranker_empty_candidates(reranker_instance):
    reranked = reranker_instance.rerank("some query", [], top_n=3)
    assert reranked == []

def test_reranker_empty_query_raises_error(reranker_instance):
    candidates = [{"chunk_id": "c1", "text": "Sample text"}]
    with pytest.raises(ValueError):
        reranker_instance.rerank("", candidates)
