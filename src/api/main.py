from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends, Request
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
import uuid
import time
import re
from loguru import logger
from prometheus_client import make_asgi_app

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from src.graph.workflow import get_compiled_graph
from src.memory.redis_store import RedisMemoryStore
from src.api.metrics import PIPELINE_RUNS_TOTAL, PIPELINE_LATENCY, ACTIVE_RUNS
from src.api.auth import verify_api_key

# Setup Rate Limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Multi-Agent IT Ops Assistant", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

memory_store = RedisMemoryStore()

# Add prometheus metrics endpoint (no auth required for internal scraping)
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

class Alert(BaseModel):
    name: str = Field(..., max_length=100)
    value: float
    host: str = Field(..., max_length=255)

class RunRequest(BaseModel):
    mode: str = Field("full", pattern="^(full|log_only|triage_only|alert_only)$")
    log_file: Optional[str] = Field(None, max_length=50000, description="Raw log content or safe path reference")
    ticket_text: Optional[str] = Field(None, max_length=5000, description="Ticket text from user")
    alerts: Optional[List[Alert]] = Field(None, max_length=100)

    @field_validator('ticket_text', 'log_file')
    @classmethod
    def prevent_prompt_injection(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        
        # Block common prompt injection phrases
        injection_patterns = [
            r"ignore\s+previous\s+instructions",
            r"you\s+are\s+now",
            r"system\s+prompt",
            r"forget\s+all"
        ]
        
        for pattern in injection_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                logger.warning(f"Blocked potential prompt injection attempt: {pattern}")
                raise ValueError("Potentially malicious prompt injection detected. Input rejected.")
                
        return v

async def execute_pipeline(run_id: str, request: RunRequest):
    logger.info(f"Starting pipeline run {run_id} in mode: {request.mode}")
    start_time = time.time()
    ACTIVE_RUNS.inc()
    try:
        memory_store.save_state(run_id, {"status": "running"})
        
        # Format payload for LangGraph
        input_state = {
            "input_data": request.model_dump()
        }
        
        # Invoke the LangGraph workflow directly via async
        graph_app = get_compiled_graph()
        result = await graph_app.ainvoke(input_state)
        
        # Format the final result
        final_state = {
            "status": "completed",
            "result": {
                "log_analysis": result.get("log_analysis", {}),
                "ticket_triage": result.get("ticket_triage", {}),
                "alert_summary": result.get("alert_summary", {}),
                "errors": result.get("errors", [])
            }
        }
        
        if final_state.get("result", {}).get("errors"):
            memory_store.push_to_dlq(run_id, input_state, str(final_state["result"]["errors"]))

        memory_store.save_state(run_id, final_state)
        PIPELINE_RUNS_TOTAL.labels(mode=request.mode, status="success").inc()
        logger.info(f"Pipeline run {run_id} completed successfully.")
        
    except Exception as e:
        logger.error(f"Pipeline run {run_id} failed: {e}")
        memory_store.save_state(run_id, {"status": "failed", "error": str(e)})
        memory_store.push_to_dlq(run_id, input_state, str(e))
        PIPELINE_RUNS_TOTAL.labels(mode=request.mode, status="failure").inc()
    finally:
        latency = time.time() - start_time
        PIPELINE_LATENCY.labels(mode=request.mode).observe(latency)
        ACTIVE_RUNS.dec()

@app.post("/run")
@limiter.limit("10/minute")
async def run_pipeline(
    request: Request,
    payload: RunRequest, 
    background_tasks: BackgroundTasks, 
    api_key: str = Depends(verify_api_key)
):
    run_id = str(uuid.uuid4())
    logger.info(f"Received request to start run: {run_id}")
    
    memory_store.save_state(run_id, {"status": "pending"})
    background_tasks.add_task(execute_pipeline, run_id, payload)
    
    return {"run_id": run_id, "status": "pending"}

@app.get("/status/{run_id}")
async def get_status(run_id: str, api_key: str = Depends(verify_api_key)):
    state = memory_store.get_state(run_id)
    if not state:
        raise HTTPException(status_code=404, detail="Run ID not found")
    return {"run_id": run_id, "status": state.get("status", "unknown")}

@app.get("/results/{run_id}")
async def get_results(run_id: str, api_key: str = Depends(verify_api_key)):
    state = memory_store.get_state(run_id)
    if not state:
        raise HTTPException(status_code=404, detail="Run ID not found")
    
    if state.get("status") != "completed":
        return {"run_id": run_id, "status": state.get("status"), "message": "Results not ready or failed"}
    
    return {"run_id": run_id, **state}

@app.get("/health")
async def health_check():
    """Health check endpoint (unauthenticated)"""
    return {"status": "healthy"}