from typing import List, Dict
from langchain_core.tools import tool

@tool
def classify_ticket_category(text: str) -> str:
    """Simple keyword-based fallback classifier."""
    text_lower = text.lower()
    
    categories = {
        "database": ["sql", "db", "postgres", "redis", "connection pool", "oom"],
        "network": ["timeout", "dns", "latency", "unreachable", "gateway"],
        "auth": ["login", "sso", "credentials", "401", "403", "password"],
        "hardware": ["disk", "cpu", "memory", "node down"]
    }
    
    for category, keywords in categories.items():
        if any(keyword in text_lower for keyword in keywords):
            return f"Infrastructure/{category.capitalize()}"
            
    return "Application/General"

@tool
def determine_priority(text: str) -> str:
    """Simple priority determination based on urgency words."""
    urgent_words = ["down", "outage", "sev1", "critical", "all users"]
    high_words = ["slow", "intermittent", "some users"]
    
    text_lower = text.lower()
    if any(word in text_lower for word in urgent_words):
        return "P1"
    elif any(word in text_lower for word in high_words):
        return "P2"
    return "P3"