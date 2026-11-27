import os
import tempfile
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
from jose import jwt
from fastapi import status
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)

def create_token(role: str) -> str:
    secret = os.getenv("JWT_SECRET_KEY", "knowvia-local-dev-secret-key-change-in-production-123456")
    algorithm = os.getenv("JWT_ALGORITHM", "HS256")
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "test_user_id",
        "role": role,
        "exp": now + timedelta(hours=1),
        "iat": now,
    }
    return jwt.encode(payload, secret, algorithm=algorithm)

def test_unauthenticated_query_denied():
    response = client.post("/api/v1/query", json={"query": "test query", "user_role": "PUBLIC_USER"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_unauthenticated_documents_list_denied():
    response = client.get("/api/v1/documents/list")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_unauthenticated_upload_denied():
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tmp:
        tmp.write(b"# Test")
        tmp_path = tmp.name
    try:
        with open(tmp_path, "rb") as f:
            response = client.post("/api/v1/documents/upload", files={"file": ("test.md", f, "text/markdown")})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def test_unauthenticated_delete_denied():
    response = client.delete("/api/v1/documents/doc_123")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_invalid_token_denied():
    headers = {"Authorization": "Bearer invalid.fake.token"}
    response = client.get("/api/v1/documents/list", headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_invalid_role_in_token_denied():
    secret = os.getenv("JWT_SECRET_KEY", "knowvia-local-dev-secret-key-change-in-production-123456")
    algorithm = os.getenv("JWT_ALGORITHM", "HS256")
    token = jwt.encode({"sub": "hacker", "role": "SUPERUSER"}, secret, algorithm=algorithm)
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/documents/list", headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_public_user_cannot_delete():
    token = create_token("PUBLIC_USER")
    headers = {"Authorization": f"Bearer {token}"}
    response = client.delete("/api/v1/documents/doc_123", headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_internal_user_cannot_delete():
    token = create_token("INTERNAL_USER")
    headers = {"Authorization": f"Bearer {token}"}
    response = client.delete("/api/v1/documents/doc_123", headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN

@patch("backend.app.api.routes_documents.get_document_service")
def test_admin_can_upload_and_delete(mock_get_doc_service):
    mock_service = MagicMock()
    mock_service.ingest_file.return_value = {
        "document_id": "doc_admin_auth_test",
        "document_name": "admin_auth_test.md",
        "total_chunks": 1,
        "status": "indexed",
        "message": "Successfully indexed 1 chunks into Qdrant & BM25."
    }
    mock_service.delete_document.return_value = True
    mock_get_doc_service.return_value = mock_service

    token_admin = create_token("ADMIN")
    headers_admin = {"Authorization": f"Bearer {token_admin}"}

    with tempfile.NamedTemporaryFile(mode="w+", suffix=".md", delete=False, encoding="utf-8") as tmp:
        tmp.write("# Admin Test")
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as f:
            upload_resp = client.post(
                "/api/v1/documents/upload",
                files={"file": ("admin_auth_test.md", f, "text/markdown")},
                data={"access_level": "PUBLIC_USER", "version": "1.0", "document_type": "technical_documentation"},
                headers=headers_admin
            )
        assert upload_resp.status_code == status.HTTP_201_CREATED
        doc_id = upload_resp.json()["document_id"]
        assert doc_id == "doc_admin_auth_test"

        # Admin delete succeeds
        delete_resp = client.delete(f"/api/v1/documents/{doc_id}", headers=headers_admin)
        assert delete_resp.status_code == status.HTTP_200_OK
        assert delete_resp.json()["document_id"] == doc_id
        mock_service.delete_document.assert_called_once_with(doc_id)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

@patch("backend.app.api.routes_query.get_intent_router")
@patch("backend.app.api.routes_query.get_hybrid_retriever")
@patch("backend.app.api.routes_query.get_reranker")
@patch("backend.app.api.routes_query.get_generation_service")
def test_cannot_elevate_role_via_request_body(mock_gen, mock_rerank, mock_retriever, mock_router):
    """
    A caller with a PUBLIC_USER token cannot elevate to ADMIN by setting
    user_role='ADMIN' in the query JSON body.
    """
    mock_router_inst = MagicMock()
    mock_route_result = MagicMock()
    from backend.app.generation.intent_router import QueryIntent
    mock_route_result.intent = QueryIntent.KNOWLEDGE
    mock_route_result.search_query = "What is the secret key?"
    mock_router_inst.route.return_value = mock_route_result
    mock_router.return_value = mock_router_inst

    mock_retriever_inst = MagicMock()
    mock_retriever_inst.retrieve.return_value = []
    mock_retriever.return_value = mock_retriever_inst

    mock_reranker_inst = MagicMock()
    mock_reranker_inst.rerank.return_value = []
    mock_rerank.return_value = mock_reranker_inst

    mock_gen_inst = MagicMock()
    mock_gen_response = MagicMock()
    mock_gen_response.answer = "Safe answer."
    mock_gen_response.citations = []
    mock_gen_response.retrieved_chunks_count = 0
    mock_gen_response.is_abstained = True
    mock_gen_response.evidence_status = "unsupported"
    mock_gen_response.supported_aspects = []
    mock_gen_response.unsupported_aspects = []
    mock_gen_inst.generate.return_value = mock_gen_response
    mock_gen_inst.generate_conversational.return_value = "Safe conversational answer."
    mock_gen.return_value = mock_gen_inst

    token_public = create_token("PUBLIC_USER")
    headers = {"Authorization": f"Bearer {token_public}"}

    # Caller attempts privilege escalation in payload
    payload = {
        "query": "What is the secret key?",
        "user_role": "ADMIN"
    }
    response = client.post("/api/v1/query", json=payload, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    # Verify that hybrid retriever received user_role from verified token (PUBLIC_USER), NOT from payload (ADMIN)
    assert mock_retriever_inst.retrieve.called
    called_kwargs = mock_retriever_inst.retrieve.call_args.kwargs
    assert called_kwargs.get("user_role") == "PUBLIC_USER"

def test_server_login_success_and_role_issuance():
    """Verify that logging in with valid credentials issues verified role tokens."""
    # 1. Admin login
    res_admin = client.post("/api/v1/auth/login", json={"username": "admin", "password": "AdminPass2026!"})
    assert res_admin.status_code == status.HTTP_200_OK
    data_admin = res_admin.json()
    assert data_admin["role"] == "ADMIN"
    assert "access_token" in data_admin

    # 2. Internal Analyst login
    res_int = client.post("/api/v1/auth/login", json={"username": "internal_analyst", "password": "InternalPass2026!"})
    assert res_int.status_code == status.HTTP_200_OK
    assert res_int.json()["role"] == "INTERNAL_USER"

    # 3. Public Guest login
    res_pub = client.post("/api/v1/auth/login", json={"username": "public_guest", "password": "GuestPass2026!"})
    assert res_pub.status_code == status.HTTP_200_OK
    assert res_pub.json()["role"] == "PUBLIC_USER"

def test_server_login_wrong_password_denied():
    """Verify that invalid credentials fail with 401 Unauthorized."""
    res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "IncorrectPassword!"})
    assert res.status_code == status.HTTP_401_UNAUTHORIZED

def test_fail_closed_when_jwt_secret_missing():
    """Verify that get_signing_secret fails closed with RuntimeError when secret is absent in authenticated mode."""
    from backend.app.security.auth import get_signing_secret
    from backend.app.core.config import settings

    orig_secret = settings.JWT_SECRET_KEY
    orig_env = os.environ.get("JWT_SECRET_KEY")
    try:
        settings.JWT_SECRET_KEY = None
        if "JWT_SECRET_KEY" in os.environ:
            del os.environ["JWT_SECRET_KEY"]

        with pytest.raises(RuntimeError) as exc_info:
            get_signing_secret()
        assert "FAILING CLOSED" in str(exc_info.value).upper()
    finally:
        settings.JWT_SECRET_KEY = orig_secret
        if orig_env:
            os.environ["JWT_SECRET_KEY"] = orig_env

def test_auth_me_endpoint():
    """Verify that GET /api/v1/auth/me returns the verified caller identity."""
    token = create_token("INTERNAL_USER")
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["role"] == "INTERNAL_USER"

def test_expired_token_denied():
    """Verify that an expired JWT token is rejected with 401 Unauthorized."""
    secret = os.getenv("JWT_SECRET_KEY", "knowvia-local-dev-secret-key-change-in-production-123456")
    algorithm = os.getenv("JWT_ALGORITHM", "HS256")
    now = datetime.now(timezone.utc)
    expired_payload = {
        "sub": "expired_user",
        "role": "ADMIN",
        "exp": now - timedelta(minutes=5),
        "iat": now - timedelta(minutes=65),
    }
    expired_token = jwt.encode(expired_payload, secret, algorithm=algorithm)
    res = client.get("/api/v1/documents/list", headers={"Authorization": f"Bearer {expired_token}"})
    assert res.status_code == status.HTTP_401_UNAUTHORIZED

def test_public_token_cannot_retrieve_internal_or_admin_dense_and_bm25():
    """
    Proves that PUBLIC_USER cannot retrieve INTERNAL or ADMIN chunks via BOTH
    dense (Qdrant) and sparse (BM25) retrieval, even when submitting forged user_role='ADMIN'.
    """
    from backend.app.retrieval.vector_store import QdrantVectorStore
    from backend.app.retrieval.dense import DenseRetriever
    from backend.app.retrieval.bm25 import BM25Retriever
    from backend.app.retrieval.hybrid import HybridRetriever
    from backend.app.embeddings.service import get_embedding_service
    from backend.app.generation.intent_router import QueryIntent, RouterResult
    from backend.app.generation.llm import MockOfflineLLMClient
    from backend.app.generation.service import GenerationService

    from backend.app.ingestion.chunker import Chunk
    embedder = get_embedding_service()
    vector_store = QdrantVectorStore(location=":memory:", collection_name="test_rbac_isolation")
    bm25 = BM25Retriever()

    c1 = Chunk("pub_1", "Kubernetes Pods are the smallest deployable units of computing.", "Public Guide")
    c2 = Chunk("int_1", "INTERNAL SECRET: Production database master password rotation occurs every 30 days.", "Internal Security Policy")
    c3 = Chunk("adm_1", "ADMIN ONLY: Root SSH recovery key fingerprint for etcd cluster.", "Admin Root Runbook")

    v1 = embedder.embed_text(c1.text)
    v2 = embedder.embed_text(c2.text)
    v3 = embedder.embed_text(c3.text)

    m1 = {"document_id": "doc_pub", "document_name": "Public Guide", "access_level": "PUBLIC_USER", "status": "active", "document_type": "technical_documentation"}
    m2 = {"document_id": "doc_int", "document_name": "Internal Security Policy", "access_level": "INTERNAL_USER", "status": "active", "document_type": "policy"}
    m3 = {"document_id": "doc_adm", "document_name": "Admin Root Runbook", "access_level": "ADMIN", "status": "active", "document_type": "runbook"}

    vector_store.add_chunks([c1, c2, c3], [v1, v2, v3], [m1, m2, m3])
    bm25.index_chunks([c1, c2, c3], [m1, m2, m3])

    dense = DenseRetriever(vector_store=vector_store, embedding_service=embedder)
    hybrid = HybridRetriever(dense_retriever=dense, bm25_retriever=bm25)

    class DeterministicKnowledgeRouter:
        def route(self, query, chat_history=None, usage_callback=None):
            return RouterResult(intent=QueryIntent.KNOWLEDGE, search_query=query)

    class PassthroughReranker:
        def rerank(self, query, candidates, top_n=5):
            return candidates[:top_n]

    # 1. Direct Dense & BM25 check for PUBLIC_USER
    dense_pub = dense.retrieve("password rotation root SSH recovery key", user_role="PUBLIC_USER", top_k=5)
    bm25_pub = bm25.retrieve("password rotation root SSH recovery key", user_role="PUBLIC_USER", top_k=5)
    assert all(r.get("access_level") in ("PUBLIC_USER", "public") for r in dense_pub)
    assert all(r.get("access_level") in ("PUBLIC_USER", "public") for r in bm25_pub)
    assert not any(r.get("chunk_id") in ("int_1", "adm_1") for r in dense_pub)
    assert not any(r.get("chunk_id") in ("int_1", "adm_1") for r in bm25_pub)

    # 2. Verify INTERNAL_USER can see internal, but not ADMIN
    dense_int = dense.retrieve("password rotation root SSH recovery key", user_role="INTERNAL_USER", top_k=5)
    bm25_int = bm25.retrieve("password rotation root SSH recovery key", user_role="INTERNAL_USER", top_k=5)
    assert any(r.get("chunk_id") == "int_1" for r in dense_int)
    assert any(r.get("chunk_id") == "int_1" for r in bm25_int)
    assert not any(r.get("chunk_id") == "adm_1" for r in dense_int)
    assert not any(r.get("chunk_id") == "adm_1" for r in bm25_int)

    # 3. End-to-end /api/v1/query with PUBLIC_USER token + forged user_role="ADMIN" in body
    pub_token = create_token("PUBLIC_USER")
    with (
        patch("backend.app.api.routes_query.get_hybrid_retriever", return_value=hybrid),
        patch("backend.app.api.routes_query.get_intent_router", return_value=DeterministicKnowledgeRouter()),
        patch("backend.app.api.routes_query.get_reranker", return_value=PassthroughReranker()),
        patch(
            "backend.app.api.routes_query.get_generation_service",
            return_value=GenerationService(llm_client=MockOfflineLLMClient()),
        ),
    ):
        res = client.post(
            "/api/v1/query",
            json={"query": "What is the password rotation and root SSH recovery key?", "user_role": "ADMIN"},
            headers={"Authorization": f"Bearer {pub_token}"}
        )
    assert res.status_code == status.HTTP_200_OK
    body = res.json()
    assert "INTERNAL SECRET" not in body["answer"]
    assert "ADMIN ONLY" not in body["answer"]
    for cit in body.get("citations", []):
        assert cit.get("access_level") in ("PUBLIC_USER", "public")
