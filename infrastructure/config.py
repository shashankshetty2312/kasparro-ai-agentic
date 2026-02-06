import os
import logging
from groq import Groq
from langchain_core.language_models.llms import LLM
from typing import Optional, List, Any

logger = logging.getLogger(__name__)

class GroqLLM(LLM):
    # Using Any to avoid Pydantic validation issues with the raw Groq client
    client: Any = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("❌ GROQ_API_KEY not set in environment variables")
        self.client = Groq(api_key=api_key)

    @property
    def _llm_type(self) -> str:
        return "groq"

    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        try:
            response = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant that only outputs valid JSON arrays."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2048
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error("Groq API call failed: %s", str(e))
            return ""

class LLMClient:
    def __init__(self):
        self.engine = GroqLLM()

    def generate(self, prompt: str) -> str:
        """Direct access to text generation."""
        return self.engine._call(prompt)

    def as_langchain_llm(self):
        return self.engine
