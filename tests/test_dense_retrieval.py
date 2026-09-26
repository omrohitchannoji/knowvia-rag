import pytest
from backend.app.retrieval.vector_store import QdrantVectorStore
from backend.app.embeddings.service import EmbeddingService
from backend.app.retrieval.dense import DenseRetriever
from backend.app.ingestion.chunker import Chunk

@pytest.fixture
def dense_setup():
    vstore = QdrantVectorStore(collection_name="test_dense_coll", location=":memory:")
    eservice = EmbeddingService()
    
    # Ingest 3 chunks with different access levels
    c1 = Chunk("chk_pub", "FastAPI path parameters validation tutorial.", "FastAPI Core")
    c2 = Chunk("chk_int", "NexaCloud employee onboarding rules.", "Onboarding")
    c3 = Chunk("chk_rst", "Production database admin credentials and secret keys.", "Secrets")

    v1 = eservice.embed_text(c1.text)
    v2 = eservice.embed_text(c2.text)
    v3 = eservice.embed_text(c3.text)

    m1 = {"document_id": "doc1", "document_name": "FastAPI Docs", "access_level": "public", "status": "active", "document_type": "technical_documentation"}
    m2 = {"document_id": "doc2", "document_name": "Onboarding Policy", "access_level": "internal", "status": "active", "document_type": "policy"}
    m3 = {"document_id": "doc3", "document_name": "Access Policy", "access_level": "restricted", "status": "active", "document_type": "policy"}

    vstore.add_chunks([c1, c2, c3], [v1, v2, v3], [m1, m2, m3])
    
    retriever = DenseRetriever(vector_store=vstore, embedding_service=eservice)
    return retriever

def test_dense_retrieval_public_user_authorization(dense_setup):
    # PUBLIC_USER querying database secrets should ONLY get public chunks, never restricted
    results = dense_setup.retrieve("How do I get database admin keys?", user_role="PUBLIC_USER", top_k=5)
    
    assert len(results) == 1
    assert results[0]["access_level"] == "public"
    assert "admin credentials" not in results[0]["text"]

def test_dense_retrieval_internal_user_authorization(dense_setup):
    results = dense_setup.retrieve("What are the onboarding rules?", user_role="INTERNAL_USER", top_k=5)
    
    # Should get public + internal chunks, but NOT restricted
    access_levels = [r["access_level"] for r in results]
    assert "restricted" not in access_levels
    assert "internal" in access_levels or "public" in access_levels

def test_dense_retrieval_admin_authorization(dense_setup):
    results = dense_setup.retrieve("Where are the production database keys?", user_role="ADMIN", top_k=5)
    
    # ADMIN should retrieve restricted chunks
    access_levels = [r["access_level"] for r in results]
    assert "restricted" in access_levels

def test_dense_retrieval_empty_query_raises_error(dense_setup):
    with pytest.raises(ValueError):
        dense_setup.retrieve("")
