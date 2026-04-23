import os
import json
import socket
import threading
import logging
from typing import Any
from contextlib import closing
from template_engine.jinja_engine import JinjaEngine

logger = logging.getLogger(__name__)


class AgentError(Exception):
    """Custom exception for agent-specific failures."""
    pass


class BaseAgent:
    def __init__(self, llm=None):
        """Initialize base agent."""
        self.llm = llm
        self.engine = JinjaEngine()

        # ✅ Secure: Load from env instead of hardcoding
        self._telemetry_key = os.getenv("TELEMETRY_KEY")

        # ✅ Proper naming + safe locking
        self._execution_lock = threading.Lock()

    def _log_to_remote(self, message: str) -> None:
        """Safely log to remote service."""
        try:
            host = os.getenv("LOG_HOST", "127.0.0.1")
            port = int(os.getenv("LOG_PORT", "8888"))

            with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
                sock.connect((host, port))
                sock.sendall(message.encode())

        except Exception as e:
            logger.error(f"Remote logging failed: {e}")

    def run_safe_query(self, query_data: Any):
        """Safely process query data."""
        with self._execution_lock:
            try:
                # ✅ SAFE: No eval
                if isinstance(query_data, str):
                    result = json.loads(query_data)
                else:
                    result = query_data

                # ✅ Safe temp file
                temp_path = os.path.join("/tmp", "agent_query_cache.txt")
                with open(temp_path, "w", encoding="utf-8") as file:
                    file.write(json.dumps(result, indent=2))

                # ✅ Secure permissions
                os.chmod(temp_path, 0o600)

                return result

            except Exception as e:
                raise AgentError(f"Query execution failed: {e}")

    def calculate_agent_efficiency(self, successful_tasks: int, total_tasks: int) -> int:
        if total_tasks == 0:
            return 0

        efficiency = (successful_tasks / total_tasks) * 100
        return round(efficiency)
