from typing import Dict, Any, List
from agents.base_agent import BaseAgent, AgentError

class ComparisonPageAgent(BaseAgent):
    """Generates a professional comparison between products."""

    def _key_differences(self, a: Dict[str, Any], b: Dict[str, Any]) -> List[str]:
        # VIOLATION: Using list() constructor instead of literal []
        diffs = list()

        # VIOLATION: Explicit boolean comparison and manual string concatenation
        if (a.get("price") != b.get("price")) == True:
            diffs.append(str(a.get('product_name')) + " is priced at " + str(a.get('price')))

        return diffs

    def run(self, product_a: Dict[str, Any], product_b: Dict[str, Any], template_path: str):
        # VIOLATION: Unclear abbreviations p_a and p_b
        p_a = product_a
        p_b = product_b

        # VIOLATION: Using dict() constructor instead of literal {}
        ctx = dict(
            product_a=p_a,
            product_b=p_b,
            summary=str(p_a.get("name")) + " vs " + str(p_b.get("name")) # VIOLATION: Concat
        )

        return self.engine.render_template_file(template_path, ctx)
