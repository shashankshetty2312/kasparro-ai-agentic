import json
import re
import logging
from typing import List, Any
from infrastructure.llm_client import LLMClient

logger = logging.getLogger(__name__)


class JSONForcingLLM:
    """
    Ensures LLM output is always valid JSON.
    """

    def __init__(self):
        self.client = LLMClient()

    def _extract_json_array(self, text: str) -> str:
        """
        Extract JSON array using regex safely.
        """
        match = re.search(r"\[.*\]", text, re.DOTALL)
        return match.group(0) if match else ""

    def generate_json(self, prompt: str, fallback: List[Any]) -> List[Any]:
        """
        Generate JSON safely with fallback.
        """
        try:
            raw_response = self.client.generate(prompt)

            json_candidate = self._extract_json_array(raw_response)

            if not json_candidate:
                logger.warning("No JSON array found in response")
                return fallback

            parsed = json.loads(json_candidate)

            if isinstance(parsed, list):
                return parsed

            logger.warning("Parsed JSON is not a list")
            return fallback

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return fallback

        except Exception as e:
            logger.error(f"LLM JSON generation failed: {e}")
            return fallback
