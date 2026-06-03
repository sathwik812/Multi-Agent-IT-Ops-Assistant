# Architecture & Design Decisions

This document details the architectural choices, trade-offs, and scaling strategies for the Multi-Agent IT Ops Assistant. Building a robust, multi-agent system for production IT Operations requires stringent requirements around determinism, observability, and fault tolerance.

## 1. Agent Orchestration: LangGraph vs. CrewAI vs. AutoGen
**Decision:** LangGraph
**Rationale:** IT Operations require deterministic routing and high reliability. Frameworks like CrewAI rely heavily on LLM-driven "role-playing" to pass control between agents, which introduces unacceptable stochasticity (e.g., an agent deciding not to pass the baton, or hallucinating the recipient). LangGraph models the workflow as a formal State Machine (DAG).
**Trade-offs:** We trade the fast, natural-language setup of CrewAI for the verbose, explicit edge definitions of LangGraph. This guarantees that execution paths (like early exits via conditional routing) are strictly defined in code, not inferred by an LLM.

## 2. Structured LLM Outputs (Pydantic vs. Prompt Engineering)
**Decision:** Langchain `with_structured_output` enforcing Pydantic schemas.
**Rationale:** Raw text generation is notoriously brittle in production pipelines. We must guarantee that the output of the Log Agent (e.g., extracting an `error_type`) can be safely consumed by the downstream Alert Summariser Agent.
**Trade-offs:** Pydantic validation adds a slight overhead and requires models that support structured output (like `gpt-4o`). However, if the LLM hallucinates a schema, Langchain automatically triggers a retry with formatting instructions, dramatically reducing parser errors downstream.

## 3. Workflow Engine: Apache Airflow vs. Celery Beat vs. Temporal
**Decision:** Apache Airflow
**Rationale:** The system requires both scheduled executions (e.g., polling logs every 5 minutes) and event-driven triggers (e.g., incoming webhooks from PagerDuty). Airflow excels at managing Directed Acyclic Graphs (DAGs) of tasks, providing superior observability, complex retry semantics (via sensors), and alerting natively.
**Trade-offs:** Airflow is heavy. For a pure event-driven system, Temporal might offer lower latency, but Airflow is ubiquitous in enterprise Ops environments, lowering the adoption barrier for the target audience.

## 4. State Persistence: Redis vs. PostgreSQL
**Decision:** Redis
**Rationale:** LangGraph state and API run statuses are highly transient. Once an incident is summarized and pushed to Slack/Jira, the raw conversational state of the graph is no longer mission-critical. Redis provides sub-millisecond read/writes, ideal for the high-frequency polling on the `/status/{run_id}` endpoint.
**Future Extension:** For long-term analytics on agent performance (e.g., triage accuracy over time), we would implement a background worker to flush completed Redis payloads to a persistent data lake (S3) or PostgreSQL.

## 5. Model Selection Strategy: GPT-4o vs. Local/Open Source Models
**Decision:** API-driven foundational model (GPT-4o/Claude) with fallback architecture.
**Rationale:** The initial cognitive load of log analysis and alert correlation requires a frontier model.
**Trade-offs:** Data privacy is a concern with SaaS models. The architecture is designed via Langchain to allow seamless swapping to self-hosted models (e.g., Llama-3-70B via vLLM) by changing the initialization in the agent classes, assuming the infrastructure can support the inference requirements.

## 6. Microservices Boundary: FastAPI vs. Monolith
**Decision:** Asynchronous FastAPI application layer.
**Rationale:** By decoupling the orchestration layer (Airflow) from the execution layer (LangGraph API), we can scale the API horizontally behind a load balancer to handle bursts of events (e.g., an alert storm). FastAPI's native async capabilities allow the web server to handle thousands of concurrent polling requests while background tasks process the LangGraph workflows.

## 7. Error Handling and Graceful Degradation
**Decision:** Agent-level Try/Catch with Mock Fallbacks.
**Rationale:** In a production ops scenario, an LLM API timeout should not crash the entire pipeline. The graph nodes are wrapped in try/except blocks. If `analyze_logs` fails, the state machine records the error in the `AgentState` list and proceeds, allowing the `TicketTriage` agent to still attempt processing based on whatever partial data exists.

## 8. Dynamic Graph Routing (Conditional Edges)
**Decision:** Implementing `mode`-based conditional routing in LangGraph.
**Rationale:** Not all events require the full pipeline. A simple alert webhook (`mode="alert_only"`) should not waste tokens running the Log Analyser. The LangGraph implementation uses `add_conditional_edges` from the `START` node and between stages to dynamically prune the DAG based on the initial payload context.

## 9. Observability and Telemetry
**Decision:** Prometheus + Grafana + Loguru.
**Rationale:** We cannot manage what we cannot measure.
- **Custom Metrics:** We instrumented the code with specific metrics (`ops_agent_tasks_total`, `ops_pipeline_latency_seconds`, `ops_slack_notifications_total`) using the `prometheus_client` SDK. This allows us to track agent performance, pipeline health, and delivery success separately from generic system metrics.
- **Alerting:** We implemented Prometheus alerting rules (`infra/alert_rules.yml`) to detect high agent failure rates (>10%) and latency degradation before users report them.
- **Visualization:** Grafana is pre-configured via automated provisioning (`infra/grafana/provisioning`) to ensure the dashboard environment is portable and reproducible.

## 10. Duplicate Alert Suppression (Stateful Tools)
**Decision:** Local deduplication in the Alert Formatter tool.
**Rationale:** Alert storms often send 100s of identical payloads. Instead of asking the LLM to deduplicate (which burns context window and tokens), we use deterministic Python logic (`src/tools/alert_formatter.py`) to hash and suppress identical alerts *before* they enter the LLM prompt.

## 11. Security and Credential Management
**Decision:** `.env` injection at runtime, never in source.
**Rationale:** Standard practice, but crucial. API keys and Slack webhooks are injected via the Docker environment or Airflow connections, ensuring no sensitive data is leaked into the repository. 

## 12. Testing Strategy for Non-Deterministic Systems
**Decision:** Pytest with environment mocking.
**Rationale:** Testing LLMs in CI/CD is flaky. The test suite uses `monkeypatch` to strip the `OPENAI_API_KEY`, forcing the agents into their deterministic fallback paths. This allows the CI pipeline to verify the LangGraph routing logic and API layer independently of the LLM provider's uptime or response variability.

## 13. Alert Actionability (Closing the Loop)
**Decision:** Formatted Slack Block Kit messages.
**Rationale:** A summary is useless if it's hard to read. The `AlertSummariserAgent` specifically outputs formatted markdown designed for Slack Block Kit, ensuring that the generated incident reports are immediately actionable by human engineers on mobile or desktop.

## 14. API Security and Rate Limiting
**Decision:** Dependency-injected API Key auth + `slowapi` rate limiting.
**Rationale:** Exposing an orchestrator that triggers heavy LLM logic (GPT-4o) without protection is a massive financial and security risk. 
- **Authentication (Fail Loudly):** We implemented FastAPI's `Security(APIKeyHeader)`. Crucially, if the `API_SECRET_KEY` environment variable is not configured, the system fails loudly with an `HTTP 500` instead of falling back to a weak default. This ensures secure-by-default behavior.
- **Rate Limiting:** We integrated `slowapi` to restrict the `/run` endpoint to `10 requests/minute` per IP. This explicitly prevents accidental webhook loops or DDoS attacks from instantly exhausting OpenAI API quotas.

## 15. Container Security (Least Privilege)
**Decision:** Executing the Docker container as a non-root user.
**Rationale:** Running containers as root is a critical vulnerability that allows potential container breakouts. The `Dockerfile` explicitly creates an `appuser` and assigns ownership of the working directory before executing the FastAPI layer via `USER appuser`, ensuring compliance with enterprise Kubernetes security standards.

## 16. Prompt Injection Defense (Defense-in-Depth)
**Decision:** Pydantic length boundaries + regex filtering + XML delimiters.
**Rationale:** IT Ops tickets are user-generated, meaning they are a prime vector for prompt injection. We applied a defense-in-depth strategy:
1. **Size Limits:** The Pydantic model caps `ticket_text` at 5,000 characters to prevent buffer overflow attacks on the context window.
2. **Regex Filtering:** A `@field_validator` scans the payload before it even reaches LangGraph, rejecting obvious injection vectors (e.g., "ignore previous instructions").
3. **Prompt Framing:** Inside the LangChain prompt templates, user input is securely wrapped in XML tags (e.g., `<ticket>{ticket}</ticket>`), and the system prompt explicitly instructs the LLM to treat the tagged content as inert data, nullifying jailbreak attempts.

## 17. Orchestration Database (PostgreSQL vs SQLite)
**Decision:** PostgreSQL for Airflow Meta-Database.
**Rationale:** Out of the box, Airflow defaults to SQLite. While fine for local testing, SQLite uses file-level locking. Under the load of an active `airflow-scheduler` and `airflow-webserver` writing concurrently, SQLite will instantly suffer from `database is locked` errors and catastrophic corruption. We provisioned a dedicated `postgres:13` container and an `airflow-init` service to execute database migrations (`airflow db migrate`), strictly adhering to Airflow production architecture.

## 18. Multi-Stage Docker Builds
**Decision:** Implementation of a 2-stage `builder` and `runtime` Dockerfile.
**Rationale:** To minimize the production image size and security surface area, we use a multi-stage build. 
1. The **builder** stage installs heavy build dependencies (like `build-essential`) needed for certain Python wheels.
2. The **runtime** stage copies only the final compiled site-packages and app code, resulting in an image that is hundreds of megabytes smaller and lacks common exploit tools (compilers, etc.).

## 19. Strict Startup Dependencies (Healthchecks)
**Decision:** Use of `service_healthy` and `service_completed_successfully` in Docker Compose.
**Rationale:** A common "distributed system" failure is services crashing because their dependencies (DB, Redis) aren't ready yet.
- We implemented `HEALTHCHECK` instructions for Postgres and Redis.
- We used advanced `depends_on` conditions in `docker-compose.yml` to ensure the Airflow Webserver ONLY starts after `airflow-init` has successfully completed its migrations. This prevents the "crash-loop on first boot" issue common in simpler setups.

## 20. Observability Security (Grafana Auth)
**Decision:** Strict Grafana authentication.
**Rationale:** Observability dashboards often expose sensitive operational metadata and infrastructure topography. We strictly disabled anonymous access in Grafana (`GF_AUTH_ANONYMOUS_ENABLED=false` implicitly by removing the override) and enforce authentication using credentials injected via `.env` (`GRAFANA_PASSWORD`).