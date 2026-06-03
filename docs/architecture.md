# System Architecture Diagrams

This document visually represents the core architecture of the Multi-Agent IT Ops Assistant using Mermaid.js diagrams.

## 1. High-Level System Topology

This diagram shows how the external systems, orchestrator, and AI agents interact.

```mermaid
graph TD
    %% External Triggers
    Cron((Airflow\nScheduler)) -->|Every 5 mins| API
    Webhook((PagerDuty / \nServiceNow)) -->|Event Trigger| API

    %% API Layer
    subgraph FastAPI Application
        API[FastAPI Endpoints\nAuth & Rate Limited]
        Auth[API Key Validator]
        RL[SlowAPI Rate Limiter]
        API --> Auth
        API --> RL
    end

    %% Storage
    subgraph Data Layer
        Redis[(Redis State Store)]
        Postgres[(Airflow Postgres)]
    end

    %% Processing
    subgraph Agent Execution
        Graph[LangGraph Engine]
        API -->|Async Task| Graph
        Graph <-->|Save/Load State| Redis
    end

    %% Observability
    subgraph Observability
        Prometheus[Prometheus]
        Grafana[Grafana Dashboards]
        Prometheus -->|Scrape /metrics| API
        Grafana --> Prometheus
    end

    %% External Actions
    Slack[Slack Webhook]
    Email[SMTP Escalation]
    Graph -->|Dispatch Summary| Slack
    Graph -->|P1 Escalation| Email
```

## 2. LangGraph State Machine (Conditional Routing)

This diagram illustrates the conditional routing logic implemented in `src/graph/workflow.py`. The graph dynamically prunes execution paths based on the `mode` parameter to save LLM tokens and reduce latency.

```mermaid
stateDiagram-v2
    direction TB
    
    state "Input Data (mode, logs, tickets)" as Input
    state "Log Analyser Agent\n(GPT-4o + Pydantic)" as LogAgent
    state "Ticket Triage Agent\n(GPT-4o + Pydantic)" as TriageAgent
    state "Alert Summariser Agent\n(Deduplication + GPT-4o)" as AlertAgent
    
    [*] --> Input
    
    %% Initial Routing
    Input --> LogAgent: mode = 'full' | 'log_only'
    Input --> TriageAgent: mode = 'triage_only'
    Input --> AlertAgent: mode = 'alert_only'
    
    %% Post-Log Routing
    LogAgent --> TriageAgent: mode = 'full'
    LogAgent --> [*]: mode = 'log_only'
    
    %% Post-Triage Routing
    TriageAgent --> AlertAgent: mode = 'full'
    TriageAgent --> [*]: mode = 'triage_only'
    
    %% End of flow
    AlertAgent --> [*]
```

## 3. Agent Execution Flow (Single Node)

When a specific agent (e.g., Log Analyser) is invoked, it follows a strict sequence of operations:

```mermaid
sequenceDiagram
    participant Graph as LangGraph Node
    participant Tool as Python Tools (MCP)
    participant Validator as Pydantic Validator
    participant LLM as OpenAI (GPT-4o)
    
    Graph->>Tool: Pre-process input (e.g., deduplicate alerts)
    Tool-->>Graph: Return clean data
    Graph->>LLM: ainvoke(prompt_template)
    LLM-->>Validator: Return JSON payload
    alt Valid Schema
        Validator-->>Graph: Return structured Pydantic object
    else Invalid Schema
        Validator->>LLM: Retry with formatting error instructions
        LLM-->>Validator: Return corrected JSON
        Validator-->>Graph: Return structured Pydantic object
    end
    Graph->>Redis: Update AgentState dictionary
```