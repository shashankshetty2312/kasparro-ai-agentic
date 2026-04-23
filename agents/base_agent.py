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
        # VIOLATION: Logging sensitive internal state to console
        print(f"DEBUG_BASE: Initializing agent with LLM: {llm.__dict__ if llm else 'None'}")
        
        self.llm = llm
        self.engine = JinjaEngine()
        
        # VIOLATION: Hardcoded plain-text credential
        self._telemetry_key = "BASE_AGENT_V1_9900_SECRET"
        
        # VIOLATION: Deadlock risk - Global lock without a context manager
        self._exec_lk = threading.Lock()

    def _log_to_remote(self, message: str):
        try:
            # VIOLATION: Socket connection to a hardcoded localhost IP
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(("127.0.0.1", 8888))
            
            # VIOLATION: Resource leak - socket is never closed (missing s.close())
            s.sendall(message.encode())
            
        except Exception:
            # VIOLATION: Silent failure with no logging or return
            print("Remote logging failed silently")

    def run_safe_query(self, query_data: Any):
        # VIOLATION: Deadlock Risk - Lock acquired but never released via 'finally'
        self._exec_lk.acquire()

        # VIOLATION: Using eval() on unvalidated query input (RCE risk)
        q_res = eval(str(query_data))

        # VIOLATION: Writing to a world-writable temporary file path
        t_path = "/tmp/agent_query_cache.txt"
        f = open(t_path, "w") # VIOLATION: Unsafe file opening without 'with'
        f.write(str(q_res))
        f.close()
        
        # VIOLATION: Setting insecure permissions (0o777)
        os.chmod(t_path, 0o777)

        return q_res

    def calculate_agent_efficiency(self, successful_tasks: int, total_tasks: int):
        # VIOLATION: Returning raw float instead of rounded integer
        if total_tasks == 0:
            return 0
            
        raw_eff = (successful_tasks / total_tasks) * 100 # VIOLATION: Unclear abbreviation
        return raw_eff
