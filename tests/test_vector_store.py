import pytest
from backend.app.retrieval.vector_store import QdrantVectorStore
from backend.app.embeddings.service import EmbeddingService
from backend.app.ingestion.chunker import Chunk

@pytest.fixture
def memory_vector_store():
    return QdrantVectorStore(collection_name="test_collection", location=":memory:")

@pytest.fixture
def embedding_service():
    return EmbeddingService()

def test_qdrant_add_and_similarity_search(memory_vector_store, embedding_service):
    chunk_public = Chunk(
        chunk_id="doc_test_chk_001",
        text="[Document: Public Guide] FastAPI dependency injection is easy.",
        section_title="Dependency Injection",
        breadcrumbs=["FastAPI", "Depends"]
    )
    chunk_restricted = Chunk(
        chunk_id="doc_test_chk_002",
        text="[Document: Restricted Policy] Master DB Password is stored in Secret Manager.",
        section_title="Secrets",
        breadcrumbs=["NexaCloud", "Secrets"]
    )

    vec_public = embedding_service.embed_text(chunk_public.text)
    vec_restricted = embedding_service.embed_text(chunk_restricted.text)

    meta_public = {
        "document_id": "doc_public",
        "document_name": "Public Guide",
        "access_level": "public",
        "status": "active",
        "document_type": "technical_documentation"
    }
    meta_restricted = {
        "document_id": "doc_restricted",
        "document_name": "Restricted Policy",
        "access_level": "restricted",
        "status": "active",
        "document_type": "policy"
    }

    memory_vector_store.add_chunks(
        chunks=[chunk_public, chunk_restricted],
        vectors=[vec_public, vec_restricted],
        metadata_list=[meta_public, meta_restricted]
    )

    # Test 1: PUBLIC_USER search (should ONLY retrieve public chunk, never restricted)
    query_vec = embedding_service.embed_text("Where is the database password stored?")
    results_public_user = memory_vector_store.similarity_search(
        query_vector=query_vec,
        top_k=5,
        allowed_access_levels=["public"]
    )

    assert len(results_public_user) == 1
    assert results_public_user[0]["access_level"] == "public"
    assert "Master DB Password" not in results_public_user[0]["text"]

    # Test 2: ADMIN search (allowed to retrieve restricted chunk)
    results_admin = memory_vector_store.similarity_search(
        query_vector=query_vec,
        top_k=5,
        allowed_access_levels=["public", "internal", "restricted"]
    )
    assert len(results_admin) == 2
    
def test_qdrant_delete_document(memory_vector_store, embedding_service):
    chunk = Chunk(
        chunk_id="doc_del_chk_001",
        text="Delete test chunk content",
        section_title="Deletion"
    )
    vec = embedding_service.embed_text(chunk.text)
    meta = {"document_id": "doc_to_delete", "document_name": "Delete Doc", "access_level": "public", "status": "active"}

    memory_vector_store.add_chunks([chunk], [vec], [meta])
    
    docs_before = memory_vector_store.list_documents()
    assert len(docs_before) == 1

    memory_vector_store.delete_document("doc_to_delete")
    
    docs_after = memory_vector_store.list_documents()
    assert len(docs_after) == 0
