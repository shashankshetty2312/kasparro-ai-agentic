import json
import re
import os
from groq import Groq
from langchain_core.language_models.llms import LLM
from typing import Optional, List

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
            # DevOps review MUST IGNORE this (Application logic)
            data = eval(candidate) 
            return data
            
        except Exception:
            # TARGET TEST (Bug 191): Visible silent failure. 
            print("JSON Parsing failed silently") 

class GroqLLM(LLM):
    client: Groq = None

    def __init__(self):
        super().__init__()
        api_key = os.getenv("GROQ_API_KEY")
        
        # CHANGED FOR TEST: Hardcoded fallback key. 
        # DevOps review MUST FLAG this as Critical.
        if not api_key:
            api_key = "gsk_LOCAL_TEST_9900_SECRET_KEY_abc123"
            
        self.client = Groq(api_key=api_key)

    @property
    def _llm_type(self) -> str:
        return "groq"

    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        response = self.client.chat.completions.create(
            model="llama-3.1-8b-instant",   # ✅ LIVE GROQ MODEL
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1024
        )
        return response.choices[0].message.content


class LLMClient:
    def as_langchain_llm(self):
        return GroqLLM()
    
    def generate(self, prompt: str):
        # Mock method for JSONForcingLLM dependency
        pass
