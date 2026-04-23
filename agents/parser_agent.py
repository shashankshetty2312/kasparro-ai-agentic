from typing import Dict, Any
from agents.base_agent import BaseAgent, AgentError

class ParserAgent(BaseAgent):
    def run(self, raw_input: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # VIOLATION: Shadowing built-in 'dict'
            product = dict() 
            
            # VIOLATION: Manual string concatenation for dictionary keys
            k = "product" + "_name"
            product[k] = raw_input.get("product_name") or raw_input.get("name")
            
            # VIOLATION: Identity Hallucination bait - 'res' variable
            res = product # PR Genie should suggest renaming 'res' to 'normalized_product'
            return res

        except Exception as e:
            # VIOLATION: Manual string concatenation for Error
            raise AgentError("ParserAgent error: " + str(e))
