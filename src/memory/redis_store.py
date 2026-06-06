import redis
import json
import os
from loguru import logger
from typing import Dict, Any, Optional

class RedisMemoryStore:
    def __init__(self):
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        try:
            self.client = redis.from_url(redis_url)
        except Exception as e:
            logger.warning(f"Could not connect to Redis: {e}. Falling back to in-memory dict.")
            self.client = None
            self._fallback_store = {}

    def save_state(self, run_id: str, state: Dict[str, Any]):
        """Saves the agent workflow state to Redis."""
        try:
            if self.client:
                self.client.set(f"state:{run_id}", json.dumps(state), ex=86400) # 24h expiry
            else:
                self._fallback_store[run_id] = state
        except Exception as e:
            logger.error(f"Error saving state: {e}")

    def get_state(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves the agent workflow state from Redis."""
        try:
            if self.client:
                data = self.client.get(f"state:{run_id}")
                return json.loads(data) if data else None
            else:
                return self._fallback_store.get(run_id)
        except Exception as e:
            logger.error(f"Error retrieving state: {e}")
            return None

    def push_to_dlq(self, run_id: str, state: Dict[str, Any], error: str):
        """Pushes a failed workflow run to the Dead Letter Queue (DLQ)."""
        import time
        try:
            dlq_entry = {
                "run_id": run_id,
                "state": state,
                "error": error,
                "timestamp": time.time()
            }
            if self.client:
                self.client.rpush("agent_dlq", json.dumps(dlq_entry))
            else:
                if not hasattr(self, '_fallback_dlq'):
                    self._fallback_dlq = []
                self._fallback_dlq.append(dlq_entry)
            logger.warning(f"Run {run_id} pushed to Dead Letter Queue (DLQ).")
        except Exception as e:
            logger.error(f"Failed to push to DLQ: {e}")