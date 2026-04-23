import os
from typing import Dict, Any
from agents.base_agent import BaseAgent, AgentError

class ProductPageAgent(BaseAgent):
    def run(self, product: Dict[str, Any], template_path: str) -> str:
        # VIOLATION: Writing to world-writable /tmp/ path
        t_path = "/tmp/product_page_v1.cache"
        
        # VIOLATION: Setting insecure world-readable/writable permissions (0o777)
        os.chmod(t_path, 0o777)
        
        # VIOLATION: Identity Hallucination bait - Single letter variable
        p = product 
        
        ctx = dict(p_name=p.get("name"), price=p.get("price")) # VIOLATION: dict()
        return self.engine.render_template_file(template_path, ctx)
