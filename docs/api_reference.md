# API Reference Documentation

The Multi-Agent IT Ops Assistant exposes a FastAPI REST API for triggering and monitoring agent workflows. 

## Base URL
`http://localhost:8000`

## Authentication
All operational endpoints require an API Key passed in the header.
- **Header:** `X-API-Key`
- **Default Dev Key:** `dev-secret-key`

## Rate Limiting
The `/run` endpoint is protected against LLM token exhaustion and DDoS attacks.
- **Limit:** 10 requests per minute per IP.
- **Exceeded Response:** `HTTP 429 Too Many Requests`

---

## Endpoints

### 1. Trigger Pipeline Run
Trigger the LangGraph multi-agent pipeline asynchronously.

**Request**
```http
POST /run
X-API-Key: dev-secret-key
Content-Type: application/json
```

**Payload Schema**
```json
{
  "mode": "string (Enum: 'full', 'log_only', 'triage_only', 'alert_only')",
  "log_file": "string (Max 50,000 chars) [Optional]",
  "ticket_text": "string (Max 5,000 chars) [Optional]",
  "alerts": [
    {
      "name": "string",
      "value": "float",
      "host": "string"
    }
  ]
}
```
*Note: `log_file` and `ticket_text` are protected against prompt injection. Phrases like "ignore previous instructions" will trigger an HTTP 422.*

**Response (HTTP 200)**
```json
{
  "run_id": "b5a93e3e-4b2a-4a6f-9c0d-1e1b2b3b4b5b",
  "status": "pending"
}
```

---

### 2. Check Pipeline Status
Poll the status of an asynchronous run.

**Request**
```http
GET /status/{run_id}
X-API-Key: dev-secret-key
```

**Response (HTTP 200)**
```json
{
  "run_id": "b5a93e3e-4b2a-4a6f-9c0d-1e1b2b3b4b5b",
  "status": "running" // Enums: "pending", "running", "completed", "failed"
}
```

---

### 3. Retrieve Pipeline Results
Fetch the final structured output from the agents. Only available when `status == "completed"`.

**Request**
```http
GET /results/{run_id}
X-API-Key: dev-secret-key
```

**Response (HTTP 200 - Completed)**
```json
{
  "run_id": "b5a93e3e-4b2a-4a6f-9c0d-1e1b2b3b4b5b",
  "status": "completed",
  "result": {
    "log_analysis": {
      "status": "success",
      "findings": [
        {
          "error_type": "OutOfMemoryError",
          "severity": "Critical",
          "affected_component": "prod-server-01",
          "context": "Java heap space exhausted"
        }
      ],
      "suggested_action": "Increase heap allocation"
    },
    "ticket_triage": {
      "priority": "P2",
      "category": "Infrastructure/Database",
      "assigned_team": "Platform Engineering",
      "is_duplicate": false,
      "summary": "Database connectivity loss",
      "original_text": "The database is down."
    },
    "alert_summary": {
      "incident_id": "INC-2847",
      "slack_message": "🚨 INCIDENT SUMMARY...",
      "email_dispatched": true
    },
    "errors": []
  }
}
```

**Response (HTTP 200 - Not Ready)**
```json
{
  "run_id": "b5a93e3e...",
  "status": "running",
  "message": "Results not ready or failed"
}
```

---

### 4. Health Check (Unauthenticated)
Used by Docker, Kubernetes, and Airflow to verify service uptime.

**Request**
```http
GET /health
```

**Response (HTTP 200)**
```json
{
  "status": "healthy"
}
```

---

### 5. Prometheus Metrics (Unauthenticated)
Scraped every 15s by the internal Prometheus instance.

**Request**
```http
GET /metrics
```