import pytest
import json
from unittest.mock import patch, MagicMock
from app.rag_pipeline import RAGPipeline

@pytest.fixture
def mock_embeddings_json(tmp_path):
    """Creates a dummy embeddings.json file for isolated testing."""
    file_path = tmp_path / "dummy_embeddings.json"
    dummy_data = [
        {
            "id": "doc_1",
            "text": "Goa Building Regulations section 5.",
            "embedding": [0.1, 0.2, 0.3]
        }
    ]
    file_path.write_text(json.dumps(dummy_data), encoding="utf-8")
    return str(file_path)

@patch("app.rag_pipeline.genai.Client")
@patch("app.rag_pipeline.ChatGoogleGenerativeAI")
def test_pipeline_initialization(mock_chat, mock_genai, mock_embeddings_json):
    """Verify RAGPipeline initializes ChromaDB collection and LangGraph without crashing."""
    pipeline = RAGPipeline(file_path=mock_embeddings_json)
    assert pipeline.collection is not None
    assert pipeline.collection.count() == 1

@patch("app.rag_pipeline.genai.Client")
@patch("app.rag_pipeline.ChatGoogleGenerativeAI")
def test_get_embedding(mock_chat, mock_genai, mock_embeddings_json):
    """Ensure vector embeddings generator formats responses correctly."""
    mock_genai_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.embeddings[0].values = [0.1, 0.2, 0.3]
    mock_genai_instance.models.embed_content.return_value = mock_response
    mock_genai.return_value = mock_genai_instance

    pipeline = RAGPipeline(file_path=mock_embeddings_json)
    embedding = pipeline._get_embedding("Test query")
    
    assert embedding == [0.1, 0.2, 0.3]

@patch("app.rag_pipeline.genai.Client")
@patch("app.rag_pipeline.ChatGoogleGenerativeAI")
def test_answer_query_mocked(mock_chat, mock_genai, mock_embeddings_json):
    """Test full execution graph using mock LLM response."""
    # Setup mock LLM invocation result
    mock_llm_instance = MagicMock()
    mock_llm_response = MagicMock()
    mock_llm_response.content = "Building height limit is 12 meters."
    mock_llm_instance.invoke.return_value = mock_llm_response
    mock_chat.return_value = mock_llm_instance

    # Setup mock embedding client
    mock_genai_instance = MagicMock()
    mock_embed_response = MagicMock()
    mock_embed_response.embeddings[0].values = [0.1, 0.2, 0.3]
    mock_genai_instance.models.embed_content.return_value = mock_embed_response
    mock_genai.return_value = mock_genai_instance

    pipeline = RAGPipeline(file_path=mock_embeddings_json)
    result = pipeline.answer_query(query="What is the building height limit?", thread_id="t1")

    assert result["answer"] == "Building height limit is 12 meters."
    assert len(result["context"]) > 0
