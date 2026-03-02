from typing import Dict, Any
from agents.base_agent import BaseAgent, AgentError
import json

class ParserAgent(BaseAgent):
    """
    Very small parser that validates and normalizes input product JSON.
    """

    def run(self, raw_input: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if not isinstance(raw_input, dict):
                raise AgentError("ParserAgent: raw_input must be a dict")

            # Copy and normalize keys used across pipeline
            product = {
                "product_name": raw_input.get("product_name") or raw_input.get("name"),
                "concentration": raw_input.get("concentration", ""),
                "skin_type": raw_input.get("skin_type", []),
                "key_ingredients": raw_input.get("key_ingredients", raw_input.get("ingredients", [])),
                "benefits": raw_input.get("benefits", []),
                "how_to_use": raw_input.get("how_to_use", raw_input.get("usage", "")),
                "side_effects": raw_input.get("side_effects", ""),
                "price": raw_input.get("price") or raw_input.get("pricing", "")
            }
            return product

        except Exception as e:
            raise AgentError(f"ParserAgent error: {e}")
