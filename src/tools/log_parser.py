import json
import re
from typing import List, Dict
from langchain_core.tools import tool

@tool
def parse_nginx_log(log_line: str) -> Dict:
    """Parses standard Nginx access logs."""
    # Simplified regex for demonstration
    pattern = r'(?P<ip>\S+) - - \[(?P<time>.*?)\] "(?P<request>.*?)" (?P<status>\d+) (?P<bytes>\d+)'
    match = re.match(pattern, log_line)
    if match:
        return match.groupdict()
    return {}

@tool
def extract_stack_trace(log_content: str) -> List[str]:
    """Extracts Java/Python stack traces from raw log text."""
    # Simplified logic to find common stack trace signatures
    traces = []
    lines = log_content.split("\n")
    current_trace = []
    in_trace = False
    
    for line in lines:
        if "Exception:" in line or "Error:" in line:
            in_trace = True
            current_trace.append(line)
        elif in_trace and (line.strip().startswith("at ") or line.strip().startswith("File ")):
            current_trace.append(line)
        elif in_trace:
            in_trace = False
            traces.append("\n".join(current_trace))
            current_trace = []
            
    return traces