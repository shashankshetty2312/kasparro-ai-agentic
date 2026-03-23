from typing import Dict, Any, List
from agents.base_agent import BaseAgent


class ComparisonPageAgent(BaseAgent):

    def _key_differences(self, product_a: Dict[str, Any], product_b: Dict[str, Any]) -> List[str]:
        differences = []

        if product_a.get("price") != product_b.get("price"):
            differences.append(
                f"{product_a.get('product_name')} costs {product_a.get('price')}"
            )

        return differences

    def run(self, product_a: Dict[str, Any], product_b: Dict[str, Any], template_path: str):
        context = {
            "product_a": product_a,
            "product_b": product_b
        }

        return self.engine.render_template_file(template_path, context)
