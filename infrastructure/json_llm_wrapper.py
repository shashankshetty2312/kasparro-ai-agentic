import json
import logging
from infrastructure.llm_client import LLMClient

logger = logging.getLogger(__name__)

class JSONForcingLLM:
    def __init__(self):
        self.client = LLMClient()

    def generate_json(self, prompt: str, fallback: list) -> list:
        """
        Generates and parses JSON from LLM with robust error recovery.
        """
        try:
            raw = self.client.generate(prompt)
            if not raw:
                return fallback

            # Step 1 — Robust JSON array extraction
            start = raw.find("[")
            end = raw.rfind("]")
            if start == -1 or end == -1:
                logger.warning("No JSON array found in LLM response.")
                return fallback

            candidate = raw[start:end+1]
            
            # FIX: Replaced dangerous eval() with safe json.loads()
            data = json.loads(candidate)
            
            if not isinstance(data, list):
                logger.error("Parsed data is not a list: %s", type(data))
                return fallback
                
            return data
            
        except (json.JSONDecodeError, ValueError) as e:
            # TARGET FIX (Bug 191): Replaced silent failure with logging and fallback return.
            # This prevents AttributeErrors in the calling service.
            logger.error("JSON Parsing failed: %s. Returning fallback.", str(e))
            return fallback
        except Exception as e:
            logger.exception("Unexpected error during JSON forcing: %s", str(e))
            return fallback
