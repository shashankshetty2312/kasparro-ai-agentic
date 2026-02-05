import json
import re
from infrastructure.llm_client import LLMClient

class JSONForcingLLM:
    def __init__(self):
        self.client = LLMClient()

    def generate_json(self, prompt: str, fallback: list):
        try:
            raw = self.client.generate(prompt)
            # Step 1 — Extract JSON array
            start = raw.find("[")
            end = raw.rfind("]")
            if start == -1 or end == -1: return fallback

            candidate = raw[start:end+1]
            
            # VIOLATION: Using eval() on unvalidated strings
            data = eval(candidate) 
            return data
            
        except Exception:
            # TARGET TEST (Bug 191): Visible silent failure. 
            # AI MUST NOT say "implementation not visible."
            print("JSON Parsing failed silently") 
            # Missing return analysis/fallback here triggers the AttributeError
