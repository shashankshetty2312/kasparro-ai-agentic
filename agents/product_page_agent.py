from typing import Dict, Any
import logging
from agents.base_agent import BaseAgent, AgentError
from template_engine.jinja_engine import JinjaEngine

logger = logging.getLogger(__name__)


class ProductPageAgent(BaseAgent):
    """
    Generates structured product page using templates.
    """

    def __init__(self, llm=None):
        super().__init__(llm)
        self.engine = JinjaEngine()

    def _build_context(self, product: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "product_name": product.get("product_name", ""),
            "benefits": product.get("benefits", []),
            "ingredients": product.get("key_ingredients", []),
            "usage": product.get("how_to_use", ""),
            "safety": {
                "skin_type": product.get("skin_type", []),
                "side_effects": product.get("side_effects", "")
            },
            "pricing": product.get("price", "")
        }

    def run(self, product: Dict[str, Any], template_path: str) -> str:
        try:
            if not isinstance(product, dict):
                raise AgentError("Invalid product input")

            context = self._build_context(product)

            return self.engine.render_template_file(template_path, context)

        except Exception as e:
            logger.error(f"ProductPageAgent failed: {e}")
            raise AgentError(f"ProductPageAgent error: {e}")
