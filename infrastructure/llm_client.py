import os
import logging
from typing import Optional, List
from groq import Groq
from langchain_core.language_models.llms import LLM
from infrastructure.config import Config

logger = logging.getLogger(__name__)


class GroqLLM(LLM):
    """
    LangChain-compatible Groq LLM wrapper.
    """

    client: Groq = None

    def __init__(self):
        super().__init__()

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("❌ GROQ_API_KEY not set")

        self.client = Groq(api_key=api_key)

    @property
    def _llm_type(self) -> str:
        return "groq"

    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        """
        Core LLM call.
        """
        try:
            response = self.client.chat.completions.create(
                model=Config.GENERATION_MODEL or "llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant"},
                    {"role": "user", "content": prompt}
                ],
                temperature=Config.TEMPERATURE,
                max_tokens=Config.MAX_TOKENS,
                top_p=Config.TOP_P
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Groq API call failed: {e}")
            raise


class LLMClient:
    """
    Central LLM client wrapper.
    """

    def __init__(self):
        self.llm = GroqLLM()

    def generate(self, prompt: str) -> str:
        """
        Simple text generation.
        """
        return self.llm.invoke(prompt)

    def as_langchain_llm(self):
        """
        Return LangChain-compatible LLM.
        """
        return self.llm
