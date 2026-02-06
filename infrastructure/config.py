from pathlib import Path
import os
import logging
import yaml
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Project root resolution
ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

def _get_yaml_config():
    yaml_path = ROOT / "config.yaml"
    if yaml_path.exists():
        try:
            with yaml_path.open("r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error("Failed to load config.yaml: %s", str(e))
    return {}

_cfg = _get_yaml_config()

class Config:
    """
    Central configuration with hierarchical priority: ENV > YAML > Defaults
    """
    # PATHS
    INPUT_PRODUCT_DATA = os.getenv("INPUT_PRODUCT_DATA", _cfg.get("input", {}).get("product_data", "input/product_data.json"))
    OUTPUT_FAQ = os.getenv("OUTPUT_FAQ", _cfg.get("outputs", {}).get("faq", "outputs/faq.json"))
    
    # LLM SETTINGS
    QUESTION_MODEL = os.getenv("QUESTION_MODEL", _cfg.get("llm", {}).get("model", "llama-3.1-8b-instant"))
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", _cfg.get("llm", {}).get("max_tokens", 1024)))
    TEMPERATURE = float(os.getenv("TEMPERATURE", _cfg.get("llm", {}).get("temperature", 0.3)))
    
    # LANGCHAIN
    LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
    LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "kasparro-ai-agent")

    @classmethod
    def validate_paths(cls):
        """Ensures input directories exist."""
        for path_attr in [attr for attr in dir(cls) if "INPUT" in attr]:
            path = Path(getattr(cls, path_attr))
            if not path.parent.exists():
                logger.info("Creating directory: %s", path.parent)
                path.parent.mkdir(parents=True, exist_ok=True)
