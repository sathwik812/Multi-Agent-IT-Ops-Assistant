import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock
from src.agents.log_analyser import LogAnalyserAgent, LogAnalysisOutput, LogFinding
from src.agents.ticket_triage import TicketTriageAgent, TicketClassification
from src.graph.workflow import get_compiled_graph

@pytest.fixture
def clean_env(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "your-google-api-key-here")

@pytest.fixture
def active_env(monkeypatch):
    # Simulate a real API key being present
    monkeypatch.setenv("GOOGLE_API_KEY", "sk-mock-valid-key-12345")

@pytest.mark.asyncio
async def test_log_analyser_fallback(clean_env):
    agent = LogAnalyserAgent()
    sample_log = "2026-05-14 ERROR OutOfMemoryError: Java heap space"
    
    result = await agent.analyze(sample_log)
    assert result["status"] == "success"
    assert result["findings"][0]["error_type"] == "OutOfMemoryError"

@pytest.mark.asyncio
async def test_ticket_triage_fallback(clean_env):
    agent = TicketTriageAgent()
    result = await agent.triage("The database is down")
    assert result["priority"] == "P2"
    assert "Database" in result["category"]

@pytest.mark.asyncio
@patch("src.agents.log_analyser.PromptTemplate")
async def test_log_analyser_real_llm_path(mock_prompt, active_env):
    # This tests the branch where self.llm is successfully initialized
    agent = LogAnalyserAgent()
    
    # Mock the chain execution to prevent real API calls
    mock_chain = AsyncMock()
    mock_chain.ainvoke.return_value = LogAnalysisOutput(
        status="success",
        findings=[LogFinding(
            error_type="MockedLLMError",
            severity="High",
            affected_component="auth-service",
            context="Token expired"
        )],
        suggested_action="Refresh tokens"
    )
    
    # Mock the pipe operator (prompt | llm)
    mock_prompt.from_template.return_value.__or__.return_value = mock_chain
    
    result = await agent.analyze("Fake log data")
    
    # Assert the real Langchain path was executed
    assert result["status"] == "success"
    assert result["findings"][0]["error_type"] == "MockedLLMError"
    mock_chain.ainvoke.assert_called_once_with({"logs": "Fake log data"})

@pytest.mark.asyncio
@patch("src.agents.ticket_triage.PromptTemplate")
async def test_ticket_triage_real_llm_path(mock_prompt, active_env):
    agent = TicketTriageAgent()
    
    mock_chain = AsyncMock()
    mock_chain.ainvoke.return_value = TicketClassification(
        priority="P1",
        category="Infrastructure/Network",
        assigned_team="NetOps",
        is_duplicate=True,
        summary="VPN is down globally"
    )
    
    mock_prompt.from_template.return_value.__or__.return_value = mock_chain
    
    result = await agent.triage("I cannot connect to the VPN")
    
    assert result["priority"] == "P1"
    assert result["assigned_team"] == "NetOps"
    assert result["original_text"] == "I cannot connect to the VPN"
    mock_chain.ainvoke.assert_called_once()

@pytest.mark.asyncio
async def test_conditional_routing_log_only(clean_env):
    input_state = {"input_data": {"mode": "log_only", "log_file": "test log"}}
    graph_app = get_compiled_graph()
    result = await graph_app.ainvoke(input_state)
    assert "log_analysis" in result
    assert "ticket_triage" not in result
    assert "alert_summary" not in result

@pytest.mark.asyncio
async def test_conditional_routing_triage_only(clean_env):
    input_state = {"input_data": {"mode": "triage_only", "ticket_text": "test ticket"}}
    graph_app = get_compiled_graph()
    result = await graph_app.ainvoke(input_state)
    assert "log_analysis" not in result
    assert "ticket_triage" in result
    assert "alert_summary" not in result
