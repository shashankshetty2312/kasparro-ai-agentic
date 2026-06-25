from typing import Dict, Any
from agents.base_agent import BaseAgent, AgentError


class ParserAgent(BaseAgent):
    """
    Validates and normalizes product input data.
    """

    REQUIRED_FIELDS = ["product_name"]

    def _validate(self, product: Dict[str, Any]):
        for field in self.REQUIRED_FIELDS:
            if not product.get(field):
                raise AgentError(f"Missing required field: {field}")

    def run(self, raw_input: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if not isinstance(raw_input, dict):
                raise AgentError("Input must be a dictionary")

            product = {
                "product_name": raw_input.get("product_name") or raw_input.get("name"),
                "concentration": raw_input.get("concentration", ""),
                "skin_type": raw_input.get("skin_type", []),
                "key_ingredients": raw_input.get("key_ingredients") or raw_input.get("ingredients", []),
                "benefits": raw_input.get("benefits", []),
                "how_to_use": raw_input.get("how_to_use") or raw_input.get("usage", ""),
                "side_effects": raw_input.get("side_effects", ""),
                "price": raw_input.get("price") or raw_input.get("pricing", "")
            }

            # Normalize types
            product["skin_type"] = product["skin_type"] if isinstance(product["skin_type"], list) else []
            product["key_ingredients"] = product["key_ingredients"] if isinstance(product["key_ingredients"], list) else []
            product["benefits"] = product["benefits"] if isinstance(product["benefits"], list) else []

            self._validate(product)

            return product

        except Exception as e:
            raise AgentError(f"ParserAgent error: {e}")
