# agents/product_page_agent.py

from typing import Dict, Any
from agents.base_agent import BaseAgent, AgentError
import logging


logger = logging.getLogger(__name__)


class ProductPageAgent(BaseAgent):
    """
    Renders a clean product page using Jinja templates.
    Ensures validated context before rendering.
    """

    def run(self, product: Dict[str, Any], template_path: str) -> str:
        try:
            if not isinstance(product, dict):
                raise AgentError("Product must be a dictionary")

            if not template_path:
                raise AgentError("Template path is required")

            if not product.get("product_name"):
                raise AgentError("Product name is required")

            context = {
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

            rendered = self.engine.render_template_file(template_path, context)

            if not rendered:
                raise AgentError("Template rendering returned empty output")

            return rendered

        except AgentError:
            raise
        except Exception as e:
            logger.exception("Unexpected ProductPageAgent failure")
            raise AgentError(f"ProductPageAgent error: {str(e)}")
