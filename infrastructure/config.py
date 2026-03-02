from pathlib import Path
import os
from dotenv import load_dotenv
import yaml

# Project root
ROOT = Path(__file__).resolve().parents[1]

ENV_PATH = ROOT / ".env"
YAML_PATH = ROOT / "config.yaml"

# Load .env if exists
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

# Load YAML if exists
try:
    if YAML_PATH.exists():
        with YAML_PATH.open("r", encoding="utf-8") as f:
            _cfg = yaml.safe_load(f) or {}
    else:
        _cfg = {}
except Exception:
    _cfg = {}

class Config:
    """
    Central configuration with priority:
    1. .env
    2. config.yaml
    3. defaults
    """

    # ============================
    # PATHS
    # ============================

    INPUT_PRODUCT_DATA = (
        os.getenv("INPUT_PRODUCT_DATA")
        or _cfg.get("input", {}).get("product_data")
        or "input/product_data.json"
    )

    TEMPLATE_FAQ = (
        os.getenv("TEMPLATE_FAQ")
        or _cfg.get("templates", {}).get("faq")
        or "templates/faq_template.json"
    )

    TEMPLATE_PRODUCT = (
        os.getenv("TEMPLATE_PRODUCT")
        or _cfg.get("templates", {}).get("product_page")
        or "templates/product_page_template.json"
    )

    TEMPLATE_COMPARISON = (
        os.getenv("TEMPLATE_COMPARISON")
        or _cfg.get("templates", {}).get("comparison")
        or "templates/comparison_page_template.json"
    )

    OUTPUT_FAQ = (
        os.getenv("OUTPUT_FAQ")
        or _cfg.get("outputs", {}).get("faq")
        or "outputs/faq.json"
    )

    OUTPUT_PRODUCT = (
        os.getenv("OUTPUT_PRODUCT")
        or _cfg.get("outputs", {}).get("product_page")
        or "outputs/product_page.json"
    )

    OUTPUT_COMPARISON = (
        os.getenv("OUTPUT_COMPARISON")
        or _cfg.get("outputs", {}).get("comparison")
        or "outputs/comparison_page.json"
    )

    # ============================
    # LLM CONFIG
    # ============================

    QUESTION_MODEL = (
        os.getenv("QUESTION_MODEL")
        or _cfg.get("llm", {}).get("model")
        or "google/flan-t5-small"
    )

    GENERATION_MODEL = (
        os.getenv("GENERATION_MODEL")
        or _cfg.get("llm", {}).get("generation_model")
        or QUESTION_MODEL
    )

    MAX_TOKENS = int(
        os.getenv("MAX_TOKENS")
        or _cfg.get("llm", {}).get("max_tokens")
        or 256
    )

    TEMPERATURE = float(
        os.getenv("TEMPERATURE")
        or _cfg.get("llm", {}).get("temperature")
        or 0.3
    )

    TOP_P = float(
        os.getenv("TOP_P")
        or _cfg.get("llm", {}).get("top_p")
        or 0.9
    )

    MIN_QUESTIONS = int(
        os.getenv("MIN_QUESTIONS")
        or _cfg.get("llm", {}).get("min_questions")
        or 15
    )

    # ============================
    # LOGGING
    # ============================

    LOG_LEVEL = (
        os.getenv("LOG_LEVEL")
        or _cfg.get("logging", {}).get("level")
        or "INFO"
    )

    # ============================
    # LANGCHAIN
    # ============================

    LANGCHAIN_TRACING_V2 = (
        os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
    )

    LANGCHAIN_PROJECT = (
        os.getenv("LANGCHAIN_PROJECT")
        or "kasparro-ai-agent"
    )

    LANGCHAIN_VERBOSE = (
        os.getenv("LANGCHAIN_VERBOSE", "false").lower() == "true"
    )
    
    # CHANGED FOR TEST: Added a new environment variable mapping.
    # DevOps review MUST track this in environment_variable_changes.
    KASPARRO_STRICT_FALLBACK = (
        os.getenv("KASPARRO_STRICT_FALLBACK", "false").lower() == "true"
    )
