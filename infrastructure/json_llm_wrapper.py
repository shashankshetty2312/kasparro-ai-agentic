import json
import logging
from infrastructure.llm_client import LLMClient

logger = logging.getLogger(__name__)


class JSONForcingLLM:
    def __init__(self):
        self.client = LLMClient()

    def generate_json(self, prompt: str, fallback: list):
        try:
            raw = self.client.generate(prompt)

            start = raw.find("[")
            end = raw.rfind("]")

            if start == -1 or end == -1:
                return fallback

            candidate = raw[start:end + 1]

            # ✅ SAFE parsing
            return json.loads(candidate)

        except Exception as e:
            logger.error(f"JSON parsing failed: {e}")
            return fallback
