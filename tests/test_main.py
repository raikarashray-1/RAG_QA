import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
import main

client = TestClient(main.app)

@pytest.fixture(autouse=True)
def mock_rag_system():
    """Mock rag_system on startup to prevent loading embeddings or hitting APIs."""
    mock_instance = MagicMock()
    mock_instance.answer_query.return_value = {
        "answer": "Goa building code rule response.",
        "context": ["Sample context snippet 1"]
    }
    main.rag_system = mock_instance
    return mock_instance

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_chat_endpoint_success():
    payload = {"query": "What is the maximum floor height?", "thread_id": "thread_123"}
    response = client.post("/chat", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Goa building code rule response."
    assert data["context"] == ["Sample context snippet 1"]
    assert data["is_exit"] is False

def test_chat_endpoint_empty_query():
    payload = {"query": "", "thread_id": "thread_123"}
    response = client.post("/chat", json=payload)
    assert response.status_code == 400
    assert "Query cannot be empty" in response.json()["detail"]

def test_chat_endpoint_empty_thread_id():
    payload = {"query": "Hello", "thread_id": "  "}
    response = client.post("/chat", json=payload)
    assert response.status_code == 400
    assert "Thread ID cannot be empty" in response.json()["detail"]

def test_chat_endpoint_exit():
    payload = {"query": "quit", "thread_id": "thread_123"}
    response = client.post("/chat", json=payload)
    assert response.status_code == 200
    assert response.json()["is_exit"] is True
