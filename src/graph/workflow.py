import time
from typing import TypedDict, Any, Dict, Literal
from langgraph.graph import StateGraph, START, END
from loguru import logger

from src.agents.log_analyser import LogAnalyserAgent
from src.agents.ticket_triage import TicketTriageAgent
from src.agents.alert_summariser import AlertSummariserAgent
from src.api.metrics import AGENT_TASK_TOTAL, AGENT_LATENCY

# Define the state object passed between agents
class AgentState(TypedDict):
    input_data: Dict[str, Any]
    log_analysis: Dict[str, Any]
    ticket_triage: Dict[str, Any]
    alert_summary: Dict[str, Any]
    errors: list[str]

# Global agent instances (Singleton pattern) 
# Initialized at module level for optimal performance.
# The agent constructors are designed to be safe even if API keys are missing (fallbacks).
log_analyser_agent = LogAnalyserAgent()
ticket_triage_agent = TicketTriageAgent()
alert_summariser_agent = AlertSummariserAgent()

# Node functions
async def analyze_logs_node(state: AgentState):
    logger.info("Executing Log Analyser Agent")
    start_time = time.time()
    log_data = state["input_data"].get("log_file", "No logs provided")
    try:
        result = await log_analyser_agent.analyze(log_data)
        AGENT_TASK_TOTAL.labels(agent_type="log_analyser", status="success").inc()
        return {"log_analysis": result}
    except Exception as e:
        logger.error(f"Log analysis failed: {e}")
        AGENT_TASK_TOTAL.labels(agent_type="log_analyser", status="failure").inc()
        return {"errors": [f"Log analysis error: {e}"]}
    finally:
        latency = time.time() - start_time
        AGENT_LATENCY.labels(agent_type="log_analyser").observe(latency)

async def triage_ticket_node(state: AgentState):
    logger.info("Executing Ticket Triage Agent")
    start_time = time.time()
    ticket_text = state["input_data"].get("ticket_text", "No ticket text provided")
    try:
        result = await ticket_triage_agent.triage(ticket_text)
        AGENT_TASK_TOTAL.labels(agent_type="ticket_triage", status="success").inc()
        return {"ticket_triage": result}
    except Exception as e:
        logger.error(f"Ticket triage failed: {e}")
        AGENT_TASK_TOTAL.labels(agent_type="ticket_triage", status="failure").inc()
        return {"errors": [f"Ticket triage error: {e}"]}
    finally:
        latency = time.time() - start_time
        AGENT_LATENCY.labels(agent_type="ticket_triage").observe(latency)

async def summarize_alerts_node(state: AgentState):
    logger.info("Executing Alert Summariser Agent")
    start_time = time.time()
    # Combine data for summarization
    context = {
        "raw_alerts": state["input_data"].get("alerts", []),
        "log_insights": state.get("log_analysis", {}),
        "ticket_insights": state.get("ticket_triage", {})
    }
    
    try:
        result = await alert_summariser_agent.summarize(context)
        AGENT_TASK_TOTAL.labels(agent_type="alert_summariser", status="success").inc()
        return {"alert_summary": result}
    except Exception as e:
        logger.error(f"Alert summarization failed: {e}")
        AGENT_TASK_TOTAL.labels(agent_type="alert_summariser", status="failure").inc()
        return {"errors": [f"Alert summarization error: {e}"]}
    finally:
        latency = time.time() - start_time
        AGENT_LATENCY.labels(agent_type="alert_summariser").observe(latency)

# Conditional Routing Logic
def route_initial(state: AgentState) -> Literal["analyze_logs", "triage_ticket", "summarize_alerts"]:
    mode = state["input_data"].get("mode", "full")
    if mode == "triage_only":
        return "triage_ticket"
    elif mode == "alert_only":
        return "summarize_alerts"
    return "analyze_logs"

def route_after_logs(state: AgentState) -> Literal["triage_ticket", "__end__"]:
    mode = state["input_data"].get("mode", "full")
    if mode == "log_only":
        return "__end__"
    return "triage_ticket"

def route_after_triage(state: AgentState) -> Literal["summarize_alerts", "__end__"]:
    mode = state["input_data"].get("mode", "full")
    if mode == "triage_only":
        return "__end__"
    return "summarize_alerts"

# Global instance for lazy loading of the compiled graph
_compiled_graph = None

def get_compiled_graph():
    """
    Lazily compiles the LangGraph state machine.
    Uses module-level agent singletons for performance.
    """
    global _compiled_graph
    if _compiled_graph is not None:
        return _compiled_graph

    logger.info("Compiling LangGraph state machine...")
    
    # Build graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("analyze_logs", analyze_logs_node)
    workflow.add_node("triage_ticket", triage_ticket_node)
    workflow.add_node("summarize_alerts", summarize_alerts_node)

    # Define conditional entry point
    workflow.add_conditional_edges(
        START,
        route_initial,
        {
            "analyze_logs": "analyze_logs",
            "triage_ticket": "triage_ticket",
            "summarize_alerts": "summarize_alerts"
        }
    )

    # Define conditional edges between nodes
    workflow.add_conditional_edges(
        "analyze_logs",
        route_after_logs,
        {
            "triage_ticket": "triage_ticket",
            "__end__": END
        }
    )

    workflow.add_conditional_edges(
        "triage_ticket",
        route_after_triage,
        {
            "summarize_alerts": "summarize_alerts",
            "__end__": END
        }
    )

    workflow.add_edge("summarize_alerts", END)

    # Compile graph and cache it
    _compiled_graph = workflow.compile()
    return _compiled_graph