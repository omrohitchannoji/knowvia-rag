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
