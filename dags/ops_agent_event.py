from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import requests
import json
import os

default_args = {
    'owner': 'ops_team',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,
}

def handle_webhook_event(**kwargs):
    """Processes an incoming event and triggers the specific pipeline mode."""
    # In a real DAG, parameters would come from the DAG run config (webhook payload)
    dag_run = kwargs.get('dag_run')
    event_payload = dag_run.conf if dag_run else {}
    
    url = "http://api:8000/run"
    payload = {
        "mode": event_payload.get('mode', 'triage_only'),
        "ticket_text": event_payload.get('ticket_text', 'Urgent issue reported via portal.'),
    }
    
    api_key = os.getenv("API_SECRET_KEY", "dev-secret-key")
    headers = {
        'Content-Type': 'application/json',
        'X-API-Key': api_key
    }
    
    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers)
        response.raise_for_status()
        print(f"Event pipeline triggered successfully. Run ID: {response.json().get('run_id')}")
    except Exception as e:
        print(f"Failed to trigger event pipeline: {e}")
        raise

with DAG(
    'ops_agent_event_driven',
    default_args=default_args,
    description='Triggered by incoming webhooks (e.g., PagerDuty, ServiceNow)',
    schedule_interval=None, # Event driven
    start_date=datetime(2023, 1, 1),
    catchup=False,
    tags=['ops', 'ai_agents', 'event_driven'],
) as dag:

    process_event_task = PythonOperator(
        task_id='process_event',
        python_callable=handle_webhook_event,
        provide_context=True,
    )