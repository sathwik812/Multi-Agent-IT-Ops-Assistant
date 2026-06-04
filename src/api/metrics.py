from prometheus_client import Counter, Histogram, Gauge

# Pipeline Metrics
PIPELINE_RUNS_TOTAL = Counter(
    "ops_pipeline_runs_total",
    "Total number of pipeline runs",
    ["mode", "status"]
)

PIPELINE_LATENCY = Histogram(
    "ops_pipeline_latency_seconds",
    "Latency of the full pipeline execution",
    ["mode"]
)

# Agent Metrics
AGENT_TASK_TOTAL = Counter(
    "ops_agent_tasks_total",
    "Total number of agent tasks executed",
    ["agent_type", "status"]
)

AGENT_LATENCY = Histogram(
    "ops_agent_latency_seconds",
    "Latency of individual agent tasks",
    ["agent_type"]
)

# Alerting Metrics
SLACK_NOTIFICATIONS_TOTAL = Counter(
    "ops_slack_notifications_total",
    "Total number of Slack notifications sent",
    ["status"]
)

# System Health
ACTIVE_RUNS = Gauge(
    "ops_active_pipeline_runs",
    "Number of currently running pipelines"
)