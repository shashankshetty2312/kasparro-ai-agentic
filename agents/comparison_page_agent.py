from typing import Dict, Any, List
from agents.base_agent import BaseAgent


class ComparisonPageAgent(BaseAgent):
    def _key_differences(self, product_a: Dict[str, Any], product_b: Dict[str, Any]) -> List[str]:
        """
        Identify key differences between two products.
        """
        differences: List[str] = []

        if product_a.get("price") != product_b.get("price"):
            differences.append(
                f"{product_a.get('product_name')} costs {product_a.get('price')}, "
                f"while {product_b.get('product_name')} costs {product_b.get('price')}."
            )

        if product_a.get("brand") != product_b.get("brand"):
            differences.append(
                f"{product_a.get('product_name')} is from {product_a.get('brand')}, "
                f"while {product_b.get('product_name')} is from {product_b.get('brand')}."
            )

        return differences

    def run(
        self,
        product_a: Dict[str, Any],
        product_b: Dict[str, Any],
        template_path: str
    ) -> str:
        """
        Render comparison page.
        """
        context = {
            "product_a": product_a,
            "product_b": product_b,
            "differences": self._key_differences(product_a, product_b),
        }

        return self.engine.render_template_file(template_path, context)
