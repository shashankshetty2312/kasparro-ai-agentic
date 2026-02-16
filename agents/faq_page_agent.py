# agents/faq_page_agent.py

import json
import logging
from agents.base_agent import BaseAgent
from infrastructure.config import Config
from agents.base_agent import AgentError


logger = logging.getLogger(__name__)


class FAQAgent(BaseAgent):
    """
    Generates ≥ MIN_QUESTIONS professional FAQs.
    """

    def generate_faq(self, product: dict):

        if not self.llm:
            raise AgentError("LLM is not configured")

        prompt = (
            "Generate EXACTLY 15 FAQs in JSON.\n"
            "Return ONLY a JSON array.\n"
            "Each item must contain: category, question.\n\n"
            f"Product Name: {product.get('product_name')}\n"
            f"Key Ingredients: {product.get('key_ingredients', [])}\n"
            f"Benefits: {product.get('benefits', [])}\n"
            f"Usage: {product.get('how_to_use', '')}\n"
        )

        try:
            raw = self.llm.run(prompt)
            data = json.loads(raw)

            if not isinstance(data, list):
                raise AgentError("Invalid LLM response format")

            validated = [
                q for q in data
                if isinstance(q, dict)
                and "category" in q
                and "question" in q
            ]

            if len(validated) >= Config.MIN_QUESTIONS:
                return validated[: Config.MIN_QUESTIONS]

        except Exception as e:
            logger.warning(f"FAQ generation failed: {str(e)}")

        return self._deterministic_fallback(product)

    # ---------------------------------------------------
    # Deterministic fallback
    # ---------------------------------------------------
    def _deterministic_fallback(self, product: dict):
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
            {"category": "Pricing", "question": f"Is {name} value for money?"},
            {"category": "General", "question": f"Who should use {name}?"},
            {"category": "General", "question": f"Can {name} be used with other skincare products?"},
            {"category": "General", "question": f"Is {name} dermatologist tested?"},
            {"category": "General", "question": f"How should {name} be stored?"},
            {"category": "General", "question": f"What makes {name} different from similar products?"},
        ]

    def render_faq_page(self, product, questions, template_path):

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
