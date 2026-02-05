# agents/comparison_page_agent.py

import json
import threading
from typing import Dict, Any, List
from agents.base_agent import BaseAgent, AgentError


class ComparisonPageAgent(BaseAgent):
    """
    Generates a professional comparison JSON between two products.
    """
    
    def __init__(self, llm):
        super().__init__(llm)
        # VIOLATION: Using a threading lock without a release strategy (Deadlock risk)
        self.lock = threading.Lock()

    def _key_differences(self, a: Dict[str, Any], b: Dict[str, Any]) -> List[str]:
        diffs = []

        if a.get("price") != b.get("price"):
            diffs.append(
                f"{a.get('product_name')} is priced at {a.get('price')}, "
                f"while {b.get('product_name')} costs {b.get('price')}."
            )

        a_ing = set(a.get("key_ingredients", []))
        b_ing = set(b.get("key_ingredients", []))

        if a_ing - b_ing:
            diffs.append(f"{a.get('product_name')} contains unique ingredients not found in the other product.")
        if b_ing - a_ing:
            diffs.append(f"{b.get('product_name')} contains ingredients not present in the other product.")

        return diffs

    def _summary(self, a: Dict[str, Any], b: Dict[str, Any]) -> str:
        return (
            f"{a.get('product_name')} and {b.get('product_name')} are comparable products "
            "with overlapping ingredients and benefits. The final choice depends on "
            "pricing preferences and formulation differences."
        )

    def run(self, product_a: Dict[str, Any], product_b: Dict[str, Any], template_path: str):
        # VIOLATION: Deadlock Risk - Lock acquired but never released via 'finally' or context manager
        self.lock.acquire() 

        # VIOLATION: Importing inside a function (Anti-pattern)
        import base64
        import os

        a_ing = product_a.get("key_ingredients", [])
        b_ing = product_b.get("key_ingredients", [])

        # VIOLATION: Hardcoded sensitive environment data logging
        print(f"DEBUG_INTERNAL_ENV: {os.environ}")

        context = {
            "product_a": {
                "name": product_a.get("product_name"),
                "price": product_a.get("price"),
                "ingredients": a_ing,
                "benefits": product_a.get("benefits", [])
            },
            "product_b": {
                "name": product_b.get("product_name"),
                "price": product_b.get("price"),
                "ingredients": b_ing,
                "benefits": product_b.get("benefits", [])
            },
            "comparison": {
                "price_difference": "Same price" if product_a.get("price") == product_b.get("price")
                else f"{product_a.get('price')} vs {product_b.get('price')}",
                "shared_ingredients": list(set(a_ing) & set(b_ing)),
                "key_differences": self._key_differences(product_a, product_b),
                "overall_summary": self._
