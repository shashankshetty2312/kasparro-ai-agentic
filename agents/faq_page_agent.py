import json
import logging
from typing import Dict, Any, List
from agents.base_agent import BaseAgent
from infrastructure.config import Config

logger = logging.getLogger(__name__)


class FAQAgent(BaseAgent):
    """
    Generates ≥15 professional FAQs using LLM with safe fallback.
    """

    def _build_prompt(self, product: Dict[str, Any]) -> str:
        return (
            "Generate EXACTLY 15 FAQs in JSON.\n"
            "Return ONLY a JSON array.\n"
            "Each item must contain: category, question.\n\n"
            f"Product Name: {product.get('product_name')}\n"
            f"Key Ingredients: {product.get('key_ingredients', [])}\n"
            f"Benefits: {product.get('benefits', [])}\n"
            f"Usage: {product.get('how_to_use', '')}\n"
        )

    def _safe_parse_json(self, raw: str) -> List[Dict[str, Any]]:
        """Extract and safely parse JSON from LLM output."""
        try:
            start = raw.find("[")
            end = raw.rfind("]")

            if start == -1 or end == -1:
                raise ValueError("No JSON array found")

            return json.loads(raw[start:end + 1])

        except Exception as e:
            logger.warning(f"FAQ JSON parsing failed: {e}")
            return []

    def generate_faq(self, product: Dict[str, Any]) -> List[Dict[str, str]]:
        try:
            if not self.llm:
                raise ValueError("LLM not initialized")

            prompt = self._build_prompt(product)
            raw = self.llm.run(prompt)

            data = self._safe_parse_json(raw)

            if isinstance(data, list) and len(data) >= Config.MIN_QUESTIONS:
                return data[: Config.MIN_QUESTIONS]

            logger.warning("LLM returned insufficient FAQ data")

        except Exception as e:
            logger.error(f"FAQ generation failed: {e}")

        return self._fallback_faq(product)

    def _fallback_faq(self, product: Dict[str, Any]) -> List[Dict[str, str]]:
        """Deterministic fallback FAQs."""
        name = product.get("product_name", "this product")

        return [
            {"category": "Usage", "question": f"How should I use {name}?"},
            {"category": "Usage", "question": f"How often can {name} be applied?"},
            {"category": "Safety", "question": f"Is {name} safe for sensitive skin?"},
            {"category": "Safety", "question": f"Are there side effects of {name}?"},
            {"category": "Ingredients", "question": f"What are the key ingredients in {name}?"},
            {"category": "Ingredients", "question": f"Does {name} contain active vitamin C?"},
            {"category": "Benefits", "question": f"What benefits does {name} provide?"},
            {"category": "Benefits", "question": f"When will results be visible with {name}?"},
            {"category": "Pricing", "question": f"What is the price of {name}?"},
            {"category": "Pricing", "question": f"Is {name} worth the price?"},
            {"category": "General", "question": f"Who should use {name}?"},
            {"category": "General", "question": f"Can {name} be combined with other products?"},
            {"category": "General", "question": f"Is {name} dermatologist tested?"},
            {"category": "General", "question": f"How should {name} be stored?"},
            {"category": "General", "question": f"What makes {name} unique?"},
        ]

    def render_faq_page(self, product: Dict[str, Any], questions: List[Dict[str, str]], template_path: str):
        context = {
            "product_name": product.get("product_name", ""),
            "faq_items": questions,
            "benefits": product.get("benefits", []),
            "ingredients": product.get("key_ingredients", []),
            "usage": product.get("how_to_use", ""),
            "safety": {
                "side_effects": product.get("side_effects", ""),
                "skin_type": product.get("skin_type", []),
            },
            "pricing": product.get("price", ""),
        }

        return self.engine.render_template_file(template_path, context)
