import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_route_who_are_you():
    resp = client.post("/api/v1/query", json={"query": "who are u", "user_role": "PUBLIC_USER"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_abstained"] is False
    assert "NexaCloud" in data["answer"]

def test_route_out_of_scope():
    resp = client.post("/api/v1/query", json={"query": "what is the weather today?", "user_role": "PUBLIC_USER"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_abstained"] is False
    assert "specialized strictly" in data["answer"]

def test_route_meta_history():
    history = [
        {"role": "user", "content": "What is NexaCloud's RPO?"},
        {"role": "assistant", "content": "RPO is 1 hour."}
    ]
    resp = client.post("/api/v1/query", json={"query": "what was my last question", "user_role": "PUBLIC_USER", "chat_history": history})
    assert resp.status_code == 200
    data = resp.json()
    assert "RPO" in data["answer"] or "last question" in data["answer"]

