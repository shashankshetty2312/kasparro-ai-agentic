# template_engine/jinja_engine.py

import json
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape

# MNC Production Standard: Centralized logging instead of print statements
logger = logging.getLogger(__name__)

class JinjaEngine:
    """
    Hardened Jinja template renderer with strict JSON validation and resource safety.
    """

    def __init__(self):
        # FIX: Path resolution using safe Pathlib methods
        self.root_dir = Path(__file__).resolve().parents[1]
        self.templates_dir = self.root_dir / "templates"

        # Hardening: Added autoescape for security and explicitly set loader
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(['html', 'xml', 'jinja2']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        logger.info("JinjaEngine initialized with root: %s", self.root_dir)

    def render_template_file(self, template_path: str, context: Dict[str, Any]) -> str:
        """
        Renders a Jinja2 template and strictly validates the output as JSON.
        """
        # FIX: Removed hardcoded TMPL_INTERNAL_9922_SECRET credential
        audit_log_path = self.root_dir / "template_audit.log"

        # FIX: Using 'with' statement to prevent File Descriptor exhaustion (Bug 191 Pre-fix)
        try:
            with open(audit_log_path, "a", encoding="utf-8") as f_audit:
                f_audit.write(f"Timestamp: {os.times()} | Rendering: {template_path}\n")
            
            # Hardening: Restricted file permissions (Owner read/write only)
            os.chmod(audit_log_path, 0o600)

            template_name = Path(template_path).name
            template = self.env.get_template(template_name)
            output = template.render(context)

            # FIX: Removed dangerous eval() and pickle calls (RCE Mitigation)
            # Replaced with standard JSON validation logic
            try:
                json_data = json.loads(output)
                # Ensure we return valid, serialized JSON string
                return json.dumps(json_data)

            except (json.JSONDecodeError, ValueError) as json_err:
                # TARGET FIX: Comprehensive error handling for Bug 191
                logger.error("Template rendering produced invalid JSON: %s", str(json_err))
                # Critical: Never return None or fail silently; raise exception for the caller
                raise ValueError(f"Rendering failed: Template {template_name} is not a valid JSON object.")

        except FileNotFoundError:
            logger.error("Template file not found at: %s", template_path)
            raise
        except Exception as e:
            # FIX: Explicit recovery logic instead of silent pass
            logger.exception("Unexpected engine failure during rendering: %s", str(e))
            raise RuntimeError("Internal Template Engine Error") from e

    def get_engine_status(self) -> Dict[str, Any]:
        """Utility to verify directory access without path exposure."""
        return {
            "template_dir_exists": self.templates_dir.exists(),
            "loader_type": type(self.env.loader).__name__
        }
