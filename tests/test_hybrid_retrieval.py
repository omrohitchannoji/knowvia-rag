import pytest
from backend.app.retrieval.vector_store import QdrantVectorStore
from backend.app.embeddings.service import EmbeddingService
from backend.app.retrieval.dense import DenseRetriever
from backend.app.retrieval.bm25 import BM25Retriever
from backend.app.retrieval.hybrid import HybridRetriever
from backend.app.ingestion.chunker import Chunk

@pytest.fixture
def hybrid_setup():
    vstore = QdrantVectorStore(collection_name="test_hybrid_coll", location=":memory:")
    eservice = EmbeddingService()
    
    # 3 chunks:
    # C1: Has semantic match for FastAPI security + exact error code ERR-4012
    # C2: Has exact keyword ERR-4012 but low semantic match
    # C3: Restricted production DB password
    c1 = Chunk("chk_hyb_1", "FastAPI security guide explains error ERR-4012 authentication lookup.", "FastAPI Security")
    c2 = Chunk("chk_hyb_2", "Troubleshooting guide list: ERR-4012 error mapping code.", "Error Codes")
    c3 = Chunk("chk_hyb_3", "Restricted secret key for production DB master.", "Secrets")

    v1 = eservice.embed_text(c1.text)
    v2 = eservice.embed_text(c2.text)
    v3 = eservice.embed_text(c3.text)

    m1 = {"document_id": "doc1", "document_name": "FastAPI Security", "access_level": "public", "status": "active", "document_type": "technical_documentation"}
    m2 = {"document_id": "doc2", "document_name": "Error Codes", "access_level": "public", "status": "active", "document_type": "technical_documentation"}
    m3 = {"document_id": "doc3", "document_name": "Secrets Policy", "access_level": "restricted", "status": "active", "document_type": "policy"}

    vstore.add_chunks([c1, c2, c3], [v1, v2, v3], [m1, m2, m3])

    dense = DenseRetriever(vector_store=vstore, embedding_service=eservice)
    bm25 = BM25Retriever()
    bm25.index_chunks([c1, c2, c3], [m1, m2, m3])

    hybrid = HybridRetriever(dense_retriever=dense, bm25_retriever=bm25)
    return hybrid

def test_hybrid_rrf_retrieval(hybrid_setup):
    results = hybrid_setup.retrieve("What does error code ERR-4012 mean in FastAPI security?", user_role="PUBLIC_USER", top_k=5)
    
    assert len(results) >= 1
    # Top chunk should be chk_hyb_1 because it matched both Dense + BM25
    assert results[0]["chunk_id"] == "chk_hyb_1"
    assert "hybrid_score" in results[0]
    assert results[0]["fusion_method"] == "RRF"

def test_hybrid_authorization_prevents_leakage(hybrid_setup):
    # PUBLIC_USER search must NEVER return chk_hyb_3 (restricted)
    results = hybrid_setup.retrieve("production DB master secret key", user_role="PUBLIC_USER", top_k=5)
    access_levels = [r["access_level"] for r in results]
    assert "restricted" not in access_levels

def test_hybrid_weighted_fusion(hybrid_setup):
    hybrid_setup.fusion_method = "weighted"
    results = hybrid_setup.retrieve("ERR-4012 authentication", user_role="PUBLIC_USER", top_k=5)
    
    assert len(results) > 0
    assert results[0]["fusion_method"] == "Weighted"
    assert "hybrid_score" in results[0]
