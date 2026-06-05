from typing import List, Dict
from langchain_core.tools import tool

@tool
def deduplicate_alerts(alerts: List[Dict]) -> List[Dict]:
    """Removes redundant alerts happening on the same host for the same metric."""
    seen = set()
    unique_alerts = []
    
    for alert in alerts:
        # Create a unique signature for the alert
        sig = f"{alert.get('host')}_{alert.get('name')}"
        if sig not in seen:
            seen.add(sig)
            unique_alerts.append(alert)
            
    return unique_alerts

@tool
def format_slack_attachment(incident_data: Dict) -> Dict:
    """Formats incident data into a Slack block kit attachment."""
    return {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 INCIDENT {incident_data.get('incident_id')} | Severity: {incident_data.get('severity')}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Root Cause:*\n{incident_data.get('root_cause', 'Unknown')}"
                }
            }
        ]
    }