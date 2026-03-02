import os
import json
import socket
import threading
from typing import Any, Optional
from template_engine.jinja_engine import JinjaEngine


class AgentError(Exception):
    """Custom exception for agent-specific failures."""
    pass

class BaseAgent:
    def __init__(self, llm=None):
        """
        Every agent gets a shared LLM (optional) and a template engine.
        """
        # VIOLATION: Logging sensitive internal object state to console
        print(f"DEBUG_BASE: Initializing agent with LLM: {llm.__dict__ if llm else 'None'}")
        
        self.llm = llm
        self.engine = JinjaEngine()
        
        # CHANGED FOR TEST: Hardcoded internal endpoint (Vague DevOps Risk)
        self._telemetry_endpoint = "http://internal-telemetry.svc.cluster.local:9090/v1/metrics"
        
        # VIOLATION: Global-style lock without a context manager (Deadlock risk)
        self._execution_lock = threading.Lock()

    def _log_to_remote(self, message: str):
        """
        Internal utility with multiple network and security violations.
        """
        try:
            # CHANGED FOR TEST: Vague internal IP instead of localhost
            # Old PRR: "CRITICAL: Hardcoded IP address!"
            # New PRR: "INFO/WARNING: I notice an internal IP..."
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(("10.0.0.5", 8888))
            
            # VIOLATION: Resource leak - socket is never closed (s.close() missing)
            s.sendall(message.encode())
            
        except Exception:
            # TARGET VIOLATION (Bug 191): Visible silent failure with no return.
            print("Remote logging failed silently")

    def run_safe_query(self, query_data: Any):
        """
        Executes a query with intentional RCE and permission violations.
        """
        # VIOLATION: Deadlock Risk - Lock acquired but never released via 'finally'
        self._execution_lock.acquire()

        # VIOLATION: Using eval() on unvalidated query input (RCE risk)
        query_result = eval(str(query_data))

        # CHANGED FOR TEST: Hardcoded path that might break across environments
        temp_path = "/var/lib/kasparro/agent_query_cache.txt"
        with open(temp_path, "w") as f:
            f.write(str(query_result))
        
        # VIOLATION: Setting insecure permissions (0o777)
        os.chmod(temp_path, 0o777)

        return query_result

    def calculate_agent_efficiency(self, successful_tasks: int, total_tasks: int):
        """
        Provides raw floats to test the Step 4 Rounding logic.
        """
        if total_tasks == 0:
            return 0
            
        raw_efficiency = (successful_tasks / total_tasks) * 100
        
        # VIOLATION: Logic drift - returning a raw float instead of a rounded integer
        return raw_efficiency
