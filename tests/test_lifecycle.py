import os
import tempfile
import pytest
from unittest.mock import MagicMock
from backend.app.services.document_service import DocumentService
from backend.app.retrieval.vector_store import QdrantVectorStore
from backend.app.embeddings.service import EmbeddingService
from backend.app.retrieval.bm25 import BM25Retriever

@pytest.fixture
def lifecycle_service():
    memory_vector_store = QdrantVectorStore(collection_name="test_lifecycle_collection", location=":memory:")
    embedding_service = EmbeddingService()
    bm25_retriever = BM25Retriever()
    service = DocumentService(
        vector_store=memory_vector_store,
        embedding_service=embedding_service,
        bm25_retriever=bm25_retriever
    )
    return service

def test_delete_synchronization_removes_from_qdrant_and_bm25(lifecycle_service):
    content1 = """---
document_id: doc_lifecycle_001
document_name: lifecycle_policy.md
access_level: PUBLIC_USER
version: v1.0
---

# Lifecycle Policy
Data retention period for access logs is strictly 90 days under GDPR compliance.
"""
    content2 = """---
document_id: doc_other_002
document_name: kubernetes_guide.md
access_level: PUBLIC_USER
version: v1.0
---

# Kubernetes Architecture
Cluster pods and worker nodes are managed by the control plane API.
"""
    content3 = """---
document_id: doc_other_003
document_name: docker_guide.md
access_level: PUBLIC_USER
version: v1.0
---

# Docker Instructions
Containers provide isolated execution environments with containerized filesystems.
"""
    content4 = """---
document_id: doc_other_004
document_name: security_guide.md
access_level: PUBLIC_USER
version: v1.0
---

# Security Directives
Transport layer security TLS certificates must be rotated every 60 days.
"""
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".md", delete=False, encoding="utf-8") as f1, \
         tempfile.NamedTemporaryFile(mode="w+", suffix=".md", delete=False, encoding="utf-8") as f2, \
         tempfile.NamedTemporaryFile(mode="w+", suffix=".md", delete=False, encoding="utf-8") as f3, \
         tempfile.NamedTemporaryFile(mode="w+", suffix=".md", delete=False, encoding="utf-8") as f4:
        f1.write(content1); path1 = f1.name
        f2.write(content2); path2 = f2.name
        f3.write(content3); path3 = f3.name
        f4.write(content4); path4 = f4.name

    try:
        # Ingest documents
        res1 = lifecycle_service.ingest_file(path1)
        res2 = lifecycle_service.ingest_file(path2)
        res3 = lifecycle_service.ingest_file(path3)
        res4 = lifecycle_service.ingest_file(path4)
        doc_id1 = res1["document_id"]
        doc_id2 = res2["document_id"]

        assert len(lifecycle_service.all_chunks) == 4

        # Verify BM25 has chunks for doc 1
        bm25_results_before = lifecycle_service.bm25_retriever.retrieve("GDPR retention", user_role="PUBLIC_USER")
        assert len(bm25_results_before) > 0
        assert bm25_results_before[0]["document_id"] == doc_id1

        # Verify Qdrant has chunks
        qdrant_docs = lifecycle_service.vector_store.list_documents()
        assert any(d["document_id"] == doc_id1 for d in qdrant_docs)
        assert any(d["document_id"] == doc_id2 for d in qdrant_docs)

        # 2. Delete document 1
        delete_success = lifecycle_service.delete_document(doc_id1)
        assert delete_success is True
        assert len(lifecycle_service.all_chunks) == 3

        # 3. Verify BM25 no longer returns the deleted document (NO stale entries!)
        bm25_results_after = lifecycle_service.bm25_retriever.retrieve("GDPR retention", user_role="PUBLIC_USER")
        assert len(bm25_results_after) == 0

        # Verify document 2 remains searchable in BM25
        bm25_results_doc2 = lifecycle_service.bm25_retriever.retrieve("Kubernetes control plane", user_role="PUBLIC_USER")
        assert len(bm25_results_doc2) > 0
        assert bm25_results_doc2[0]["document_id"] == doc_id2

        # 4. Verify Qdrant no longer lists document 1 but still lists document 2
        qdrant_docs_after = lifecycle_service.vector_store.list_documents()
        assert not any(d["document_id"] == doc_id1 for d in qdrant_docs_after)
        assert any(d["document_id"] == doc_id2 for d in qdrant_docs_after)
    finally:
        for p in [path1, path2, path3, path4]:
            if os.path.exists(p):
                os.remove(p)

def test_repeat_ingestion_deduplication(lifecycle_service):
    content = """---
document_id: doc_repeat_001
document_name: repeat_doc.md
access_level: PUBLIC_USER
version: v1.0
---

# Repeat Document
Version 1 of the cluster deployment instructions.
"""
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(content)
        path = f.name

    try:
        # First ingestion
        res1 = lifecycle_service.ingest_file(path)
        initial_chunk_count = len(lifecycle_service.all_chunks)
        assert initial_chunk_count > 0

        # Repeat ingestion of same document
        res2 = lifecycle_service.ingest_file(path)
        repeat_chunk_count = len(lifecycle_service.all_chunks)

        # Chunk count should NOT double; old chunks were replaced/deduplicated
        assert repeat_chunk_count == initial_chunk_count
    finally:
        if os.path.exists(path):
            os.remove(path)

def test_ingestion_failure_rollback(lifecycle_service):
    # Mock BM25 failure to test transaction rollback
    mock_failing_bm25 = MagicMock()
    mock_failing_bm25.index_chunks.side_effect = RuntimeError("Simulated BM25 indexing failure")
    lifecycle_service.bm25_retriever = mock_failing_bm25

    content = """---
document_id: doc_fail_001
document_name: fail_doc.md
access_level: PUBLIC_USER
version: v1.0
---

# Failing Document
This document should be rolled back if indexing fails.
"""
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(content)
        path = f.name

    try:
        with pytest.raises(RuntimeError):
            lifecycle_service.ingest_file(path)

        # Verify Qdrant was cleaned up / rolled back
        qdrant_docs = lifecycle_service.vector_store.list_documents()
        assert not any(d["document_id"] == "doc_fail_001" for d in qdrant_docs)
    finally:
        if os.path.exists(path):
            os.remove(path)

def test_in_memory_state_rolled_back_on_partial_failure(lifecycle_service):
    """Verify that in-memory chunks and metadata rollback to pre-failure state on BM25 error."""
    # First ingest a valid document
    valid_content = """---
document_id: doc_pre_existing
document_name: pre_existing.md
access_level: PUBLIC_USER
version: v1.0
---

# Pre-existing Document
This document is already indexed and should survive the partial failure of a subsequent file.
"""
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(valid_content)
        v_path = f.name

    try:
        lifecycle_service.ingest_file(v_path)
        baseline_chunks_count = len(lifecycle_service.all_chunks)
        assert baseline_chunks_count > 0

        # Now mock BM25 index_chunks failure for next file
        real_bm25 = lifecycle_service.bm25_retriever
        mock_bm25 = MagicMock()
        mock_bm25.index_chunks.side_effect = RuntimeError("Partial failure during BM25 update")
        lifecycle_service.bm25_retriever = mock_bm25

        fail_content = """---
document_id: doc_should_abort
document_name: abort.md
access_level: PUBLIC_USER
version: v1.0
---

# Abort Doc
Should never remain in memory.
"""
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".md", delete=False, encoding="utf-8") as ff:
            ff.write(fail_content)
            fail_path = ff.name

        try:
            with pytest.raises(RuntimeError):
                lifecycle_service.ingest_file(fail_path)

            # In-memory chunks must be strictly rolled back to baseline
            assert len(lifecycle_service.all_chunks) == baseline_chunks_count
            assert not any(m.get("document_id") == "doc_should_abort" for m in lifecycle_service.all_metadata)
        finally:
            if os.path.exists(fail_path):
                os.remove(fail_path)
    finally:
        if os.path.exists(v_path):
            os.remove(v_path)

def test_delete_all_documents_clears_bm25_index_completely(lifecycle_service):
    """Verify that deleting all documents clears bm25_index to None without stale state."""
    content = """---
document_id: doc_solo
document_name: solo.md
access_level: PUBLIC_USER
version: v1.0
---

# Solo Doc
Single document in collection.
"""
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(content)
        path = f.name

    try:
        lifecycle_service.ingest_file(path)
        assert len(lifecycle_service.all_chunks) > 0
        assert lifecycle_service.bm25_retriever.bm25_index is not None

        # Delete sole document
        res = lifecycle_service.delete_document("doc_solo")
        assert res is True
        assert len(lifecycle_service.all_chunks) == 0
        assert lifecycle_service.bm25_retriever.bm25_index is None
        assert lifecycle_service.bm25_retriever.retrieve("Solo", user_role="PUBLIC_USER") == []
    finally:
        if os.path.exists(path):
            os.remove(path)
