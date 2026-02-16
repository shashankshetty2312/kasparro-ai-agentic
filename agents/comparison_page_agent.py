# agents/comparison_page_agent.py

from typing import Dict, Any, List
from agents.base_agent import BaseAgent, AgentError


class ComparisonPageAgent(BaseAgent):
    """
    Generates a professional comparison JSON between two products.
    """

    def _validate_product(self, product: Dict[str, Any]) -> None:
        if not isinstance(product, dict):
            raise AgentError("Invalid product format")

        required = ["product_name", "price"]
        for field in required:
            if field not in product:
                raise AgentError(f"Missing required field: {field}")

    def _key_differences(self, a: Dict[str, Any], b: Dict[str, Any]) -> List[str]:
        diffs = []

        if a.get("price") != b.get("price"):
            diffs.append(
                f"{a['product_name']} is priced at {a['price']}, "
                f"while {b['product_name']} costs {b['price']}."
            )

        a_ing = set(a.get("key_ingredients", []))
        b_ing = set(b.get("key_ingredients", []))

        if a_ing - b_ing:
            diffs.append(f"{a['product_name']} contains unique ingredients.")
        if b_ing - a_ing:
            diffs.append(f"{b['product_name']} contains unique ingredients.")

        return diffs

    def _summary(self, a: Dict[str, Any], b: Dict[str, Any]) -> str:
        return (
            f"{a['product_name']} and {b['product_name']} offer overlapping benefits. "
            "The decision depends on pricing and formulation preferences."
        )

    def run(self, product_a: Dict[str, Any], product_b: Dict[str, Any], template_path: str):

        self._validate_product(product_a)
        self._validate_product(product_b)

        a_ing = product_a.get("key_ingredients", [])
        b_ing = product_b.get("key_ingredients", [])

        context = {
            "product_a": {
                "name": product_a["product_name"],
                "price": product_a["price"],
                "ingredients": a_ing,
                "benefits": product_a.get("benefits", [])
            },
            "product_b": {
                "name": product_b["product_name"],
                "price": product_b["price"],
                "ingredients": b_ing,
                "benefits": product_b.get("benefits", [])
            },
            "comparison": {
                "price_difference": (
                    "Same price"
                    if product_a["price"] == product_b["price"]
                    else f"{product_a['price']} vs {product_b['price']}"
                ),
                "shared_ingredients": list(set(a_ing) & set(b_ing)),
                "key_differences": self._key_differences(product_a, product_b),
                "overall_summary": self._summary(product_a, product_b),
            }
        }

        return self.engine.render_template_file(template_path, context)
