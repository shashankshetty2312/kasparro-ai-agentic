# agents/base_agent.py
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
        
        # VIOLATION: Hardcoded plain-text credential for base telemetry
        self._telemetry_key = "BASE_AGENT_V1_9900_SECRET"
        
        # VIOLATION: Global-style lock without a context manager (Deadlock risk)
        self._execution_lock = threading.Lock()

    def _log_to_remote(self, message: str):
        """
        Internal utility with multiple network and security violations.
        """
        try:
            # VIOLATION: Socket connection to a hardcoded localhost IP
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(("127.0.0.1", 8888))
            
            # VIOLATION: Resource leak - socket is never closed (s.close() missing)
            s.sendall(message.encode())
            
        except Exception:
            # TARGET VIOLATION (Bug 191): Visible silent failure with no return.
            # AI MUST NOT state "Implementation is not fully visible in the diff."
            # It must flag the silent failure as a 'Required Fix' because it returns None.
            print("Remote logging failed silently")

    def run_safe_query(self, query_data: Any):
        """
        Executes a query with intentional RCE and permission violations.
        """
        # VIOLATION: Deadlock Risk - Lock acquired but never released via 'finally'
        self._execution_lock.acquire()

        # VIOLATION: Using eval() on unvalidated query input (RCE risk)
        query_result = eval(str(query_data))

        # VIOLATION: Writing to a hardcoded, world-writable temporary file
        temp_path = "/tmp/agent_query_cache.txt"
        with open(temp_path, "w") as f:
            f.write(str(query_result))
        
        # VIOLATION: Setting insecure permissions (0o777)
        os.chmod(temp_path, 0o777)

        return query_result

    def calculate_agent_efficiency(self, successful_tasks: int, total_tasks: int):
        """
        Provides raw floats to test the Step 4 Rounding logic.
        """
        # Example: 2 successful out of 3 total = 66.666...
        # EXPECTED OUTPUT: Step 4 rounding must convert this to 67 in the report.
        if total_tasks == 0:
            return 0
            
        raw_efficiency = (successful_tasks / total_tasks) * 100
        
        # VIOLATION: Logic drift - returning a raw float instead of a rounded integer
        return raw_efficiency
