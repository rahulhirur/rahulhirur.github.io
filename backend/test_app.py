import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Import the FastAPI app
from app import app
from providers import provider_manager

client = TestClient(app)

def test_read_root():
    """Test the welcome root endpoint config structure."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "config" in data
    assert "configured_providers" in data["config"]
    assert "available_providers" in data["config"]
    assert "scheduling_enabled" in data["config"]

@patch("app.fetch_calcom_slots")
def test_slots_endpoint(mock_fetch):
    """Test the slots endpoint returns mocked slots correctly."""
    # Setup mock response
    mock_fetch.return_value = {
        "slots": [
            {"time": "10:00", "iso": "2026-07-01T10:00:00Z", "label": "10:00 AM"}
        ]
    }
    
    response = client.get("/slots?date=2026-07-01")
    assert response.status_code == 200
    data = response.json()
    assert "slots" in data
    assert len(data["slots"]) == 1
    assert data["slots"][0]["time"] == "10:00"
    mock_fetch.assert_called_once_with(date="2026-07-01", duration=30, timezone="Asia/Kolkata")

def test_chat_no_providers():
    """Test chat returns 500 error when no LLM providers are available."""
    # Mock get_available_providers to return an empty list
    with patch.object(provider_manager, "get_available_providers", return_value=[]):
        response = client.post("/chat", json={"message": "hello", "history": []})
        assert response.status_code == 500
        assert "No LLM providers configured" in response.json()["detail"]

@patch("app.ChatOpenAI")
@patch("app.create_react_agent")
def test_chat_with_mocked_llm(mock_agent_create, mock_chat_openai):
    """Test chatbot endpoint returns mocked AI text message."""
    # Mock resolved configuration for provider
    with patch.object(provider_manager, "get_available_providers", return_value=["openai"]):
        with patch.object(provider_manager, "resolve_config", return_value=("fake-key", "fake-url", "gpt-4")):
            # Mock the agent invocation result (for agentic mode)
            mock_agent = MagicMock()
            mock_msg = MagicMock()
            mock_msg.content = "This is a mocked response about Rahul."
            mock_agent.invoke.return_value = {"messages": [mock_msg]}
            mock_agent_create.return_value = mock_agent

            # Mock standard LLM invoke result (for simple chain mode if TOOLS is empty)
            mock_llm = MagicMock()
            mock_llm_result = MagicMock()
            mock_llm_result.content = "This is a mocked response about Rahul."
            mock_llm.invoke.return_value = mock_llm_result
            mock_chat_openai.return_value = mock_llm

            response = client.post("/chat", json={"message": "Who is Rahul?", "history": []})
            assert response.status_code == 200
            assert response.json()["response"] == "This is a mocked response about Rahul."
