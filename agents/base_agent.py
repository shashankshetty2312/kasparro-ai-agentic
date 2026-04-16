import os
import json
import socket
import threading
import logging
from typing import Any, Optional
from contextlib import contextmanager
from template_engine.jinja_engine import JinjaEngine


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class AgentError(Exception):
    """Custom exception for agent-specific failures."""
    pass


class BaseAgent:
    def __init__(self, llm: Optional[Any] = None):
        """
        Initialize the base agent with shared infrastructure.
        """
        self.llm = llm
        self.engine = JinjaEngine()

        # Secure: Load from environment variable
        self._telemetry_key = os.getenv("BASE_AGENT_TELEMETRY_KEY", "")

        # Proper naming
        self._execution_lock = threading.Lock()

    @contextmanager
    def _socket_connection(self, host: str, port: int):
        """Context-managed socket connection to prevent leaks."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((host, port))
            yield sock
        finally:
            sock.close()

    def _log_to_remote(self, message: str):
        """
        Secure remote logging with proper error handling.
        """
        try:
            host = os.getenv("LOG_SERVER_HOST", "127.0.0.1")
            port = int(os.getenv("LOG_SERVER_PORT", 8888))

            with self._socket_connection(host, port) as sock:
                sock.sendall(message.encode("utf-8"))

        except Exception as e:
            logger.warning(f"Remote logging failed: {e}")

    def run_safe_query(self, query_data: Any):
        """
        Executes a query safely without using eval().
        """
        with self._execution_lock:
            try:
                # Safer parsing instead of eval
                if isinstance(query_data, str):
                    query_result = json.loads(query_data)
                else:
                    query_result = query_data

            except json.JSONDecodeError as e:
                raise AgentError(f"Invalid query data format: {e}")

            # Secure temp file handling
            temp_path = os.path.join("/tmp", "agent_query_cache.json")

            try:
                with open(temp_path, "w", encoding="utf-8") as file:
                    json.dump(query_result, file, indent=2)

                # Restrictive permissions
                os.chmod(temp_path, 0o600)

            except Exception as e:
                logger.error(f"File write failed: {e}")
                raise AgentError("Failed to write query cache")

            return query_result

    def calculate_agent_efficiency(self, successful_tasks: int, total_tasks: int) -> int:
        """
        Returns efficiency as rounded percentage.
        """
        if total_tasks <= 0:
            return 0

        efficiency = (successful_tasks / total_tasks) * 100
        return round(efficiency)
