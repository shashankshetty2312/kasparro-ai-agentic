from pathlib import Path
import os
from dotenv import load_dotenv
import yaml
import logging

logger = logging.getLogger(__name__)

# Project root
ROOT = Path(__file__).resolve().parents[1]

ENV_PATH = ROOT / ".env"
YAML_PATH = ROOT / "config.yaml"

# Load .env safely
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
    logger.info(".env loaded successfully")

# Load YAML safely
_cfg = {}
try:
    if YAML_PATH.exists():
        with YAML_PATH.open("r", encoding="utf-8") as f:
            _cfg = yaml.safe_load(f) or {}
        logger.info("config.yaml loaded successfully")
except Exception as e:
    logger.warning(f"Failed to load YAML config: {e}")


class Config:
    """
    Central configuration with priority:
    1. Environment variables (.env)
    2. config.yaml
    3. Defaults
    """

    @staticmethod
    def _get(key: str, default=None, section: str = None):
        """
        Helper method to fetch config with priority.
        """
        env_val = os.getenv(key)
        if env_val is not None:
            return env_val

        if section and section in _cfg:
            return _cfg.get(section, {}).get(key.lower(), default)

        return default

    # ============================
    # PATHS
    # ============================

    INPUT_PRODUCT_DATA = _get.__func__(
        "INPUT_PRODUCT_DATA", "input/product_data.json", "input"
    )

    TEMPLATE_FAQ = _get.__func__(
        "TEMPLATE_FAQ", "templates/faq_template.json", "templates"
    )

    TEMPLATE_PRODUCT = _get.__func__(
        "TEMPLATE_PRODUCT", "templates/product_page_template.json", "templates"
    )

    TEMPLATE_COMPARISON = _get.__func__(
        "TEMPLATE_COMPARISON", "templates/comparison_page_template.json", "templates"
    )

    OUTPUT_FAQ = _get.__func__(
        "OUTPUT_FAQ", "outputs/faq.json", "outputs"
    )

    OUTPUT_PRODUCT = _get.__func__(
        "OUTPUT_PRODUCT", "outputs/product_page.json", "outputs"
    )

    OUTPUT_COMPARISON = _get.__func__(
        "OUTPUT_COMPARISON", "outputs/comparison_page.json", "outputs"
    )

    # ============================
    # LLM CONFIG
    # ============================

    QUESTION_MODEL = _get.__func__(
        "QUESTION_MODEL", "google/flan-t5-small", "llm"
    )

    GENERATION_MODEL = _get.__func__(
        "GENERATION_MODEL", QUESTION_MODEL, "llm"
    )

    MAX_TOKENS = int(_get.__func__(
        "MAX_TOKENS", 256, "llm"
    ))

    TEMPERATURE = float(_get.__func__(
        "TEMPERATURE", 0.3, "llm"
    ))

    TOP_P = float(_get.__func__(
        "TOP_P", 0.9, "llm"
    ))

    MIN_QUESTIONS = int(_get.__func__(
        "MIN_QUESTIONS", 15, "llm"
    ))

    # ============================
    # LOGGING
    # ============================

    LOG_LEVEL = _get.__func__(
        "LOG_LEVEL", "INFO", "logging"
    )

    # ============================
    # LANGCHAIN
    # ============================

    LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"

    LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "kasparro-ai-agent")

    LANGCHAIN_VERBOSE = os.getenv("LANGCHAIN_VERBOSE", "false").lower() == "true"
