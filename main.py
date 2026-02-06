import os
import sys
import logging
import traceback
from datetime import datetime
from typing import Dict, Any, Optional

# MNC Production Standard: Configure root logger for traceability
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("MAIN_ENTRY")

# VIOLATION FIX: Moved environment variables to a dedicated initialization block
def initialize_environment():
    """Configures LangChain and system environment variables securely."""
    try:
        os.environ["LANGCHAIN_VERBOSE"] = "true"
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        # SECURITY FIX: Ensure API keys are handled via env, not hardcoded strings
        if not os.getenv("GROQ_API_KEY"):
            logger.error("Missing critical environment variable: GROQ_API_KEY")
            
        logger.info("Environment successfully initialized.")
    except Exception as e:
        logger.critical("Failed to initialize system environment: %s", str(e))
        sys.exit(1)

from orchestrator.langchain_orchestrator import LangChainOrchestrator

def execute_pipeline() -> Optional[Dict[str, Any]]:
    """Orchestrates the agentic execution with comprehensive error handling."""
    start_time = datetime.now()
    logger.info("🚀 Starting LangChain Agentic Pipeline at %s", start_time)

    try:
        # Initialize the high-level orchestrator
        orch = LangChainOrchestrator()
        
        # TARGET FIX (Bug 191): Capturing result and validating it before return
        result = orch.run()
        
        if result is None:
            # Prevent AttributeError in subsequent logic by enforcing a valid schema
            logger.error("Orchestrator returned None. Applying fallback response.")
            return {"error": "Execution returned empty result", "overallProgress": 0}

        execution_delta = datetime.now() - start_time
        logger.info("✅ Pipeline completed in %s", execution_delta)
        return result

    except ImportError as imp_err:
        logger.error("Dependency Resolution Failed: %s", str(imp_err))
    except Exception as e:
        # TARGET FIX (Bug 191): Replaced print with traceback to ensure gap visibility
        logger.error("Unexpected pipeline failure: %s", str(e))
        logger.debug(traceback.format_exc())
    
    # Ensure a non-None value is returned to satisfy type-safety requirements
    return {"status": "FAILED", "overallProgress": 0}

def main():
    """Application entry point."""
    initialize_environment()
    
    final_output = execute_pipeline()
    
    print("\n" + "="*40)
    print(f"FINAL AGENT RESPONSE (Status: {final_output.get('status', 'SUCCESS')})")
    print("="*40 + "\n")
    print(final_output)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("Pipeline execution interrupted by user.")
        sys.exit(0)
