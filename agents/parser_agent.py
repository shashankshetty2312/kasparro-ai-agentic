
# agents/parser_agent.py

from typing import Dict, Any, List
from agents.base_agent import BaseAgent, AgentError
import logging


logger = logging.getLogger(__name__)


class ParserAgent(BaseAgent):
    """
    Validates, sanitizes and normalizes raw product JSON input.
    Ensures strict schema consistency across pipeline.
    """

    REQUIRED_FIELDS = ["product_name"]

    def _ensure_list(self, value) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(v).strip() for v in value if v]
        if isinstance(value, str):
            return [value.strip()]
        return []

    def _ensure_string(self, value) -> str:
        if value is None:
            return ""
        return str(value).strip()

    def run(self, raw_input: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if not isinstance(raw_input, dict):
                raise AgentError("ParserAgent: raw_input must be a dictionary")

            product = {
                "product_name": self._ensure_string(
                    raw_input.get("product_name") or raw_input.get("name")
                ),
                "concentration": self._ensure_string(raw_input.get("concentration")),
                "skin_type": self._ensure_list(raw_input.get("skin_type")),
                "key_ingredients": self._ensure_list(
                    raw_input.get("key_ingredients") or raw_input.get("ingredients")
                ),
                "benefits": self._ensure_list(raw_input.get("benefits")),
                "how_to_use": self._ensure_string(
                    raw_input.get("how_to_use") or raw_input.get("usage")
                ),
                "side_effects": self._ensure_string(raw_input.get("side_effects")),
                "price": self._ensure_string(
                    raw_input.get("price") or raw_input.get("pricing")
                ),
            }

            # Required field validation
            for field in self.REQUIRED_FIELDS:
                if not product.get(field):
                    raise AgentError(f"Missing required field: {field}")

            return product

        except AgentError:
            raise
        except Exception as e:
            logger.exception("Unexpected ParserAgent failure")
            raise AgentError(f"ParserAgent error: {str(e)}")
