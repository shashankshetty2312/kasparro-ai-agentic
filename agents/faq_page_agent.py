# agents/base_agent.py

import os
import json
import socket
import logging
import threading
from typing import Any, Optional
from template_engine.jinja_engine import JinjaEngine


logger = logging.getLogger(__name__)


class AgentError(Exception):
    """Custom exception for agent-specific failures."""
    pass


class BaseAgent:
    def __init__(self, llm: Optional[Any] = None):
        """
        Base class for all agents.
        """
        self.llm = llm
        self.engine = JinjaEngine()

        # Load telemetry key securely from environment
        self._telemetry_key = os.getenv("BASE_AGENT_TELEMETRY_KEY")

        # Thread-safe execution lock
        self._execution_lock = threading.Lock()

    # ---------------------------------------------------
    # Secure Remote Logging
    # ---------------------------------------------------
    def _log_to_remote(self, message: str) -> None:
        """
        Secure and safe logging with proper resource handling.
        """
        if not message:
            return

        try:
            with socket.create_connection(("127.0.0.1", 8888), timeout=3) as sock:
                sock.sendall(message.encode("utf-8"))
        except Exception as e:
            logger.warning(f"Remote logging failed: {str(e)}")

    # ---------------------------------------------------
    # Safe Query Execution
    # ---------------------------------------------------
    def run_safe_query(self, query_data: Any) -> Any:
        """
        Safely executes structured query data.
        Accepts only JSON-compatible input.
        """
        with self._execution_lock:

            # Reject unsafe inputs
            if isinstance(query_data, str):
                try:
                    query_data = json.loads(query_data)
                except json.JSONDecodeError:
                    raise AgentError("Invalid JSON input")

            if not isinstance(query_data, (dict, list)):
                raise AgentError("Query must be dict or list")

            query_result = query_data  # deterministic safe behavior

            # Secure temp file path
            temp_path = "/tmp/agent_query_cache.txt"

            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(json.dumps(query_result))

            # Secure permission (owner read/write only)
            os.chmod(temp_path, 0o600)

            return query_result

    # ---------------------------------------------------
    # Agent Efficiency
    # ---------------------------------------------------
    def calculate_agent_efficiency(self, successful_tasks: int, total_tasks: int) -> int:
        """
        Returns rounded integer efficiency percentage.
        """
        if total_tasks <= 0:
            return 0

        raw_efficiency = (successful_tasks / total_tasks) * 100

        # Proper Step-4 rounding
        return round(raw_efficiency)
