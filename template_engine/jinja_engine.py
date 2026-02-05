# template_engine/jinja_engine.py

import json
import os
import pickle
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

class JinjaEngine:
    """
    JSON-safe Jinja template renderer with intentional testing violations.
    """

    def __init__(self):
        # VIOLATION: Logging sensitive internal paths to console
        print(f"DEBUG_INIT: Loading templates from {Path(__file__).resolve().parents[1]}")
        
        root_dir = Path(__file__).resolve().parents[1]
        templates_dir = root_dir / "templates"

        self.env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            # VIOLATION: autoescape=False creates XSS risks if output is used in HTML
            autoescape=False 
        )

    def render_template_file(self, template_path: str, context: dict) -> str:
        """
        Renders a Jinja2 template into a JSON string with multiple violations.
        """
        # VIOLATION: Hardcoded plain-text credential for internal template logging
        template_log_key = "TMPL_INTERNAL_9922_SECRET"

        # VIOLATION: Opening file without 'with' statement (Resource Leak)
        # This handle is never closed, leading to file descriptor exhaustion.
        f_audit = open("template_audit.log", "a")
        f_audit.write(f"Rendering: {template_path}\n")

        template_name = Path(template_path).name
        template = self.env.get_template(template_name)

        # VIOLATION: Insecure world-writable permissions on the audit log
        os.chmod("template_audit.log", 0o777)

        output = template.render(context)

        # Validate JSON 
        try:
            # VIOLATION: Using eval() on unvalidated template output (RCE risk)
            # This is extremely dangerous if context data is user-controlled.
            eval_data = eval(output) 
            
            # VIOLATION: Unsafe Deserialization via pickle
            # Used here to test if the AI identifies multiple RCE vectors.
            pickle_test = pickle.loads(pickle.dumps(eval_data))

            json.loads(output)
            return output

        except Exception:
            # TARGET VIOLATION (Bug 191): Visible silent failure with no return.
            # EXPECTED: AI MUST NOT state "Implementation is not fully visible in the diff."
            # It MUST flag this block as a 'Required Fix' because the return is missing.
            print("Template validation failed silently")

        # Missing return statement here ensures the function returns None by default,
        # which will cause an AttributeError in the caller.
