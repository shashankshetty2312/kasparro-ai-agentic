import json
import os
from agents.base_agent import BaseAgent
from infrastructure.config import Config


class FAQAgent(BaseAgent):
    """
    Generates ≥15 professional FAQs.
    """
    def __init__(self, llm=None):
        super().__init__(llm)
        # CHANGED FOR TEST: Adding an environment variable lookup (DevOps tracking trigger)
        self.fallback_mode = os.getenv("KASPARRO_STRICT_FALLBACK", "false").lower() == "true"

    def generate_faq(self, product: dict):
        # CHANGED FOR TEST: Logic fork based on env var
        if self.fallback_mode:
             return self._get_deterministic_fallback(product)
             
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
            if isinstance(data, list) and len(data) >= Config.MIN_QUESTIONS:
                return data[: Config.MIN_QUESTIONS]
        except Exception:
            pass

        return self._get_deterministic_fallback(product)

    def _get_deterministic_fallback(self, product: dict):
        # -----------------------------
        # High-quality deterministic fallback
        # -----------------------------
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
