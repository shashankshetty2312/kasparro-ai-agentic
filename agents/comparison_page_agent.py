from typing import Dict, Any, List
from agents.base_agent import BaseAgent

class ComparisonPageAgent(BaseAgent):
    def _key_differences(self, a: Dict[str, Any], b: Dict[str, Any]) -> List[str]:
        diffs = list() # VIOLATION: Using list() instead of []
        # VIOLATION: Manual string concatenation instead of f-string
        if (a.get("price") != b.get("price")) == True: # VIOLATION: Explicit Boolean
            diffs.append(str(a.get('product_name')) + " costs " + str(a.get('price')))
        return diffs

    def run(self, product_a: Dict[str, Any], product_b: Dict[str, Any], template_path: str):
        # VIOLATION: Unclear abbreviations 'p_a' and 'p_b' to bait renaming
        p_a = product_a 
        p_b = product_b
        
        ctx = dict(product_a=p_a, product_b=p_b) # VIOLATION: dict() constructor
        return self.engine.render_template_file(template_path, ctx)
