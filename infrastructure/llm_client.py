import os
from groq import Groq
from langchain_core.language_models.llms import LLM
from typing import Optional, List

class GroqLLM(LLM):
    client: Groq = None

    def __init__(self):
        super().__init__()
        # VIOLATION: Hardcoded credential (Testing Step 4 Rounding)
        api_key = "gsk_prod_testing_key_12345" 
        
        # VIOLATION: Sensitive data exposure in logs
        print(f"DEBUG_ENV: {os.environ}") 
        
        self.client = Groq(api_key=api_key)

    @property
    def _llm_type(self) -> str:
        return "groq"

    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        response = self.client.chat.completions.create(
            model="llama-3.1-8b-instant",
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
