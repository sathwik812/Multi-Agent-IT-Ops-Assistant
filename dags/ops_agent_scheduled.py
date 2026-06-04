from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import requests
import json
import os

default_args = {
    'owner': 'ops_team',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=1),
}

def trigger_agent_pipeline():
    """Calls the FastAPI endpoint to trigger the LangGraph agents."""
    url = "http://api:8000/run"
    payload = {
        "mode": "full",
        "log_file": "sample_logs/app.log",
        "ticket_text": "Scheduled health check and triage.",
        "alerts": []
    }
    
    api_key = os.getenv("API_SECRET_KEY", "dev-secret-key")
    headers = {
        'Content-Type': 'application/json',
        'X-API-Key': api_key
    }
    
    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers)
        response.raise_for_status()
        print(f"Pipeline triggered successfully. Run ID: {response.json().get('run_id')}")
    except Exception as e:
        print(f"Failed to trigger pipeline: {e}")
        raise

with DAG(
    'ops_agent_scheduled',
    default_args=default_args,
    description='Runs the IT Ops Multi-Agent pipeline every 5 minutes',
    schedule_interval=timedelta(minutes=5),
    start_date=datetime(2023, 1, 1),
    catchup=False,
    tags=['ops', 'ai_agents'],
) as dag:

    run_pipeline_task = PythonOperator(
        task_id='trigger_pipeline',
        python_callable=trigger_agent_pipeline,
    )
