import os
from groq import Groq
from langchain_core.language_models.llms import LLM
from typing import Optional, List

class GroqLLM(LLM):
    client: Groq = None

    def __init__(self):
        super().__init__()
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            # Dangerous fallback or crash
            raise ValueError("❌ GROQ_API_KEY not set")
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
        # Basic generation wrapper
        llm = GroqLLM()
        return llm._call(prompt)