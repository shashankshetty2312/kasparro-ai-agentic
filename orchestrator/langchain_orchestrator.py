import json
import logging
from langchain_core.tools import Tool
from langchain.agents import create_structured_chat_agent
from langchain.agents.agent import AgentExecutor
from langchain_core.prompts import ChatPromptTemplate

from infrastructure.llm_client import LLMClient
from infrastructure.config import Config
from agents.faq_page_agent import FAQAgent
from agents.product_page_agent import ProductPageAgent
from agents.comparison_page_agent import ComparisonPageAgent

logger = logging.getLogger(__name__)


class LangChainOrchestrator:
    def __init__(self):
        logger.info("Using Groq LLM")

        self.llm = LLMClient().as_langchain_llm()

        self.faq_agent = FAQAgent(self.llm)
        self.product_agent = ProductPageAgent(self.llm)
        self.compare_agent = ComparisonPageAgent(self.llm)

        self.tool_state = {
            "faq": False,
            "product": False,
            "comparison": False
        }

        self.tools = [
            Tool(name="generate_faq", func=self._faq_tool, description="Generate FAQ page"),
            Tool(name="generate_product_page", func=self._product_tool, description="Generate product page"),
            Tool(name="generate_comparison", func=self._comparison_tool, description="Generate comparison page")
        ]

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a tool-calling AI. Call all tools exactly once."),
            ("human", "{input}"),
            ("ai", "{agent_scratchpad}")
        ])

        self.agent = create_structured_chat_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt
        )

        self.executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            max_iterations=10
        )

    # ------------------ TOOLS ------------------

    def _faq_tool(self, product_json: str):
        if self.tool_state["faq"]:
            return "FAQ_ALREADY_DONE"

        try:
            product = json.loads(product_json)

            faqs = self.faq_agent.generate_faq(product)
            rendered = self.faq_agent.render_faq_page(
                product, faqs, Config.TEMPLATE_FAQ
            )

            with open(Config.OUTPUT_FAQ, "w", encoding="utf-8") as file:
                file.write(rendered)

            self.tool_state["faq"] = True
            return "FAQ_DONE"

        except Exception as e:
            logger.error(f"FAQ tool failed: {e}")
            return "FAQ_FAILED"

    def _product_tool(self, product_json: str):
        if self.tool_state["product"]:
            return "PRODUCT_ALREADY_DONE"

        try:
            product = json.loads(product_json)

            rendered = self.product_agent.run(product, Config.TEMPLATE_PRODUCT)

            with open(Config.OUTPUT_PRODUCT, "w", encoding="utf-8") as file:
                file.write(rendered)

            self.tool_state["product"] = True
            return "PRODUCT_DONE"

        except Exception as e:
            logger.error(f"Product tool failed: {e}")
            return "PRODUCT_FAILED"

    def _comparison_tool(self, product_json: str):
        if self.tool_state["comparison"]:
            return "COMPARE_ALREADY_DONE"

        try:
            product = json.loads(product_json)

            rendered = self.compare_agent.run(
                product, product, Config.TEMPLATE_COMPARISON
            )

            with open(Config.OUTPUT_COMPARISON, "w", encoding="utf-8") as file:
                file.write(rendered)

            self.tool_state["comparison"] = True
            return "COMPARE_DONE"

        except Exception as e:
            logger.error(f"Comparison tool failed: {e}")
            return "COMPARE_FAILED"

    # ------------------ RUN ------------------

    def run(self):
        try:
            with open(Config.INPUT_PRODUCT_DATA, "r", encoding="utf-8") as file:
                product = json.load(file)

            prompt_str = (
                "Call all tools to generate pages.\n\n"
                + json.dumps(product)
            )

            result = self.executor.invoke({
                "input": prompt_str,
                "agent_scratchpad": ""
            })

            return {
                "faq": Config.OUTPUT_FAQ,
                "product": Config.OUTPUT_PRODUCT,
                "comparison": Config.OUTPUT_COMPARISON,
                "agent_result": result
            }

        except Exception as e:
            logger.error(f"Orchestrator failed: {e}")
            raise
