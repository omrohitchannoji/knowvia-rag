import pytest
from backend.app.retrieval.bm25 import BM25Retriever, tokenize_text
from backend.app.ingestion.chunker import Chunk

@pytest.fixture
def bm25_setup():
    c1 = Chunk(
        chunk_id="doc_bm25_chk_001",
        text="[Document: FastAPI Security] Error code ERR-4012 represents auth lookup failure.",
        section_title="Security"
    )
    c2 = Chunk(
        chunk_id="doc_bm25_chk_002",
        text="[Document: Docker Guide] Use flag --platform=linux/amd64 during multi-stage build.",
        section_title="Docker Build"
    )
    c3 = Chunk(
        chunk_id="doc_bm25_chk_003",
        text="[Document: Restricted Access] Production DB master secret password key is prod-secret-1234.",
        section_title="Restricted Keys"
    )

    m1 = {"document_id": "doc1", "document_name": "FastAPI Security", "access_level": "public", "status": "active", "document_type": "technical_documentation"}
    m2 = {"document_id": "doc2", "document_name": "Docker Guide", "access_level": "public", "status": "active", "document_type": "technical_documentation"}
    m3 = {"document_id": "doc3", "document_name": "Restricted Access", "access_level": "restricted", "status": "active", "document_type": "policy"}

    retriever = BM25Retriever()
    retriever.index_chunks([c1, c2, c3], [m1, m2, m3])
    return retriever

def test_tokenize_text():
    text = "OAuth2PasswordBearer error code ERR-4012 --reload-dir"
    tokens = tokenize_text(text)
    assert "oauth2passwordbearer" in tokens
    assert "err-4012" in tokens
    assert "reload-dir" in tokens

def test_bm25_exact_error_code_retrieval(bm25_setup):
    results = bm25_setup.retrieve("ERR-4012", user_role="PUBLIC_USER", top_k=5)
    assert len(results) > 0
    assert results[0]["chunk_id"] == "doc_bm25_chk_001"
    assert "ERR-4012" in results[0]["text"]

def test_bm25_authorization_filtering(bm25_setup):
    # PUBLIC_USER querying for prod-secret-1234 should NOT get restricted chunk
    results_public = bm25_setup.retrieve("prod-secret-1234", user_role="PUBLIC_USER", top_k=5)
    assert len(results_public) == 0

    # ADMIN querying for prod-secret-1234 should get restricted chunk
    results_admin = bm25_setup.retrieve("prod-secret-1234", user_role="ADMIN", top_k=5)
    assert len(results_admin) == 1
    assert results_admin[0]["access_level"] == "restricted"

def test_bm25_empty_query_raises_error(bm25_setup):
    with pytest.raises(ValueError):
        bm25_setup.retrieve("")
