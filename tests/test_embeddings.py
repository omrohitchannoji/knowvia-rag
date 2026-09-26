import pytest
from backend.app.embeddings.service import EmbeddingService

def test_embedding_service_dimension():
    service = EmbeddingService()
    text = "FastAPI dependency injection authentication"
    vec = service.embed_text(text)
    
    assert isinstance(vec, list)
    assert len(vec) == 384, f"Expected 384 dimension vector, got {len(vec)}"

def test_embedding_batch():
    service = EmbeddingService()
    texts = [
        "Docker container security guidance",
        "NexaCloud production database access rules",
        "OWASP top 10 web application vulnerabilities"
    ]
    vectors = service.embed_batch(texts)
    
    assert len(vectors) == 3
    for v in vectors:
        assert len(v) == 384

def test_empty_string_embedding_raises_error():
    service = EmbeddingService()
    with pytest.raises(ValueError):
        service.embed_text("")
