# 🤖 Multi-Agent IT Ops Assistant — LangGraph + Airflow + MCP

> A production-style multi-agent system where specialised AI agents collaborate to autonomously handle IT operations tasks — log analysis, ticket triage, and alert summarisation — orchestrated by Apache Airflow and exposed via FastAPI.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2-purple)
![Airflow](https://img.shields.io/badge/Apache_Airflow-2.9-red?logo=apacheairflow)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-green?logo=fastapi)
![Prometheus](https://img.shields.io/badge/Prometheus-monitoring-red?logo=prometheus)
![Docker](https://img.shields.io/badge/Docker-ready-blue?logo=docker)

---

## 🔍 What Problem Does This Solve?

IT operations teams face a constant flood of alerts, log entries, and support tickets. First-level triage — reading logs, classifying severity, routing tickets, summarising incidents — is repetitive, time-consuming, and often the bottleneck betwesen detection and resolution.

This system deploys **three specialised AI agents** that work together to:
- **Analyse logs** and identify root-cause patterns autonomously
- **Triage and classify** incoming support tickets without human intervention
- **Summarise alerts** into actionable incident reports delivered via Slack

Inspired by real-world IT operations experience managing CIM workflows, ServiceNow dashboards, and SLA tracking across enterprise clients.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        AGENT ORCHESTRATION                       │
│                    LangGraph State Machine                       │
│                                                                 │
│   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐       │
│   │  Log Analyser│──▶│ Ticket Triage│──▶│Alert Summary │       │
│   │    Agent     │   │    Agent     │   │    Agent     │       │
│   └──────────────┘   └──────────────┘   └──────────────┘       │
│           │                  │                  │               │
│           └──────────────────┴──────────────────┘               │
│                        Shared Memory Layer                       │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATION LAYER                         │
│         Apache Airflow — Scheduled + Event-Driven DAGs           │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                        API & ALERTING LAYER                      │
│   FastAPI endpoints  ·  Slack webhooks  ·  Email notifications   │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                       OBSERVABILITY LAYER                        │
│          Prometheus metrics  ·  Loguru structured logs           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🤖 The Three Agents

### 1. Log Analyser Agent
- **Input:** Raw log files (plain text, JSON structured logs)
- **Task:** Identify error patterns, anomalies, and root-cause indicators
- **Output:** Structured incident report (error type, affected component, severity, suggested action)
- **Tools:** Log parser, pattern matcher, LLM reasoning chain

### 2. Ticket Triage Agent
- **Input:** Incoming support ticket text
- **Task:** Classify priority (P1–P4), assign category, route to appropriate team, detect duplicates
- **Output:** Enriched ticket with priority, category, suggested assignee, duplicate flag
- **Tools:** Keyword classification chain, ServiceNow-style routing rules

### 3. Alert Summariser Agent
- **Input:** Raw monitoring alerts (Prometheus/Grafana format)
- **Task:** Deduplicate, correlate, and summarise a batch of alerts into a single actionable incident report
- **Output:** Slack-ready incident summary with severity, affected systems, recommended actions
- **Tools:** Alert deduplication logic, LLM summarisation, Slack webhook

---

## ✨ Key Features

| Feature | Details |
|---|---|
| **Multi-Agent Coordination** | LangGraph state machine with typed message passing between agents |
| **Workflow Orchestration** | Apache Airflow DAGs — scheduled (every 5 min) and event-triggered |
| **Fault Tolerance** | Tenacity retry logic + dead-letter queue (DLQ) in Redis for non-recoverable failures |
| **Tool Integration** | Agents equipped with modular LangChain tools (log parser, ticket classifier, alert formatter) |
| **API Layer** | FastAPI endpoints — trigger agents via REST or Slack slash commands |
| **Observability** | Prometheus metrics: agent task outcomes, latency, error rates per agent |
| **Structured Logging** | Loguru JSON logs with correlation IDs per workflow run |
| **Alerting** | Context-rich Slack summaries + Email escalation for unresolved P1s |
| **Shared Memory** | Redis-backed conversation memory across agent turns |

---

## 🛠️ Tech Stack

- **Agent Orchestration:** LangGraph
- **Workflow Scheduling:** Apache Airflow 2.9
- **API Layer:** FastAPI
- **LLM Backend:** Google Gemini (1.5 Pro) API
- **Retry Logic:** Tenacity
- **Monitoring:** Prometheus + Loguru
- **Alerting:** Slack Webhooks, Twilio (SMS), SMTP Email
- **Infra:** Docker Compose, AWS EC2

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Google Gemini API key
- Slack Webhook URL (for alerting)

### 1. Clone the repo
```bash
git clone https://github.com/yourusername/multi-agent-ops-assistant
cd multi-agent-ops-assistant
```

### 2. Set up environment
```bash
cp .env.example .env
# Fill in: GOOGLE_API_KEY, SLACK_WEBHOOK_URL, REDIS_URL
pip install -e .[dev]
```

### 3. Start all services
```bash
docker-compose up --build
# Airflow UI:   http://localhost:8080  (admin / admin)
# FastAPI docs: http://localhost:8000/docs
# Prometheus:   http://localhost:9090
```

### 4. Trigger the agent pipeline manually
```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-secret-key" \
  -d '{"mode": "full", "log_file": "sample_logs/app.log"}'
```

---

## 📁 Project Structure

```
multi-agent-ops-assistant/
├── src/
│   ├── agents/
│   │   ├── log_analyser.py      # Log analysis agent
│   │   ├── ticket_triage.py     # Ticket classification agent
│   │   └── alert_summariser.py  # Alert summarisation agent
│   ├── graph/
│   │   └── workflow.py          # LangGraph state machine definition
│   ├── tools/
│   │   ├── log_parser.py        # LangChain tool: log parsing & pattern matching
│   │   ├── classifier.py        # LangChain tool: ticket category classification
│   │   └── alert_formatter.py   # LangChain tool: alert deduplication & formatting
│   ├── memory/
│   │   └── redis_store.py       # Shared memory layer & DLQ (Redis)
│   ├── api/
│   │   └── main.py              # FastAPI: /run, /status, /results endpoints
│   └── alerting/
│       ├── slack.py             # Slack webhook integration
│       ├── twilio_notify.py     # Twilio SMS escalation (P1 incidents)
│       └── email_notify.py      # SMTP email escalation (P1/P2 incidents)
├── dags/
│   ├── ops_agent_scheduled.py   # Airflow DAG: runs every 5 minutes
│   └── ops_agent_event.py       # Airflow DAG: event-triggered
├── infra/
│   ├── docker-compose.yml
│   ├── Dockerfile
│   └── prometheus.yml
├── sample_logs/
│   └── app.log                  # Sample log file for testing
├── docs/
│   ├── architecture.md          # Mermaid architecture and graph diagrams
│   ├── api_reference.md         # Detailed API docs, schemas, and Auth setup
│   └── design.md                # 19-point architectural decision log
├── tests/
│   ├── test_log_analyser.py
│   ├── test_ticket_triage.py
│   └── test_alert_summariser.py
├── .env.example
└── README.md
```

---

## 📊 API Reference

### `POST /run`
Trigger the full agent pipeline.
```json
{
  "mode": "full | log_only | triage_only | alert_only",
  "log_file": "path/to/logs.log",
  "ticket_text": "Application is down, users cannot login",
  "alerts": [{"name": "HighCPU", "value": 98, "host": "prod-server-01"}]
}
```

### `GET /status/{run_id}`
Poll the status of an async pipeline run.

### `GET /results/{run_id}`
Retrieve the final structured output from all agents.

---

## 📈 Sample Output

**Alert Summariser Agent → Slack:**
```
🚨 INCIDENT SUMMARY  |  Severity: P2  |  14:32 UTC

Affected Systems: prod-server-01, prod-db-02
Root Cause (Log Analyser): OOM condition on prod-server-01 causing cascading DB timeouts
Correlated Alerts: 7 alerts → 1 incident (6 duplicates suppressed)

Recommended Actions:
  1. Restart application service on prod-server-01
  2. Scale DB connection pool (current: 50, recommended: 100)
  3. Review memory allocation in next deployment

Ticket #INC-2847 created and routed to: Platform Engineering Team
```

---

## 🔑 Design Decisions

See [`docs/design.md`](docs/design.md) for the full write-up. Key decisions:

- **LangGraph over CrewAI** — typed state machine gives deterministic message passing; CrewAI's role-play model was too unpredictable for production ops use cases
- **Airflow over custom scheduler** — battle-tested, observable, and familiar to ops teams; DAG-based retries handle partial failures cleanly
- **Redis shared memory** — lightweight, fast, and sufficient for intra-run context; PostgreSQL overkill for this use case
- **Separate agents vs. single chain** — specialisation improves reliability; a single chain handling all three tasks hallucinated significantly more on the log analysis subtask

---

## 🗺️ Roadmap

- [ ] LangSmith tracing for full agent reasoning observability
- [ ] Fine-tuned open-source LLM (Mistral 7B via QLoRA) for log classification
- [ ] Auto-remediation agent (restart services, scale resources via cloud APIs)
- [ ] Integration with PagerDuty and ServiceNow APIs
- [ ] Web dashboard for agent run history and outcomes

---

## 📝 License

MIT License — see [LICENSE](LICENSE)

---

*Built by [Sathwik] · [LinkedIn](https://linkedin.com/in/yourprofile) · [Portfolio](https://github.com/yourusername)*