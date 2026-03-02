from typing import Dict, Any
from agents.base_agent import BaseAgent, AgentError
from template_engine.jinja_engine import JinjaEngine

class ProductPageAgent(BaseAgent):
    """
    Renders a clean product page JSON using Jinja.
    """

    def __init__(self, llm=None):
        super().__init__(llm)
        self.engine = JinjaEngine()
        
        # CHANGED FOR TEST: Hardcoded generic webhook. 
        # Old code: "CRITICAL: Hardcoded URL"
        # New code: "INFO: Consider moving to env var"
        self._cache_webhook = "https://cache-service.internal:8000/flush"

    def run(self, product: Dict[str, Any], template_path: str) -> str:
        try:
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

            return self.engine.render_template_file(template_path, context)

        except Exception as e:
            raise AgentError(f"ProductPageAgent error: {e}")
