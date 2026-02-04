import json
import os
import shutil
import tempfile
from langchain_core.tools import Tool
from langchain.agents import create_structured_chat_agent
from langchain.agents.agent import AgentExecutor
from langchain_core.prompts import ChatPromptTemplate

from infrastructure.llm_client import LLMClient
from infrastructure.config import Config
from agents.faq_page_agent import FAQAgent
from agents.product_page_agent import ProductPageAgent
from agents.comparison_page_agent import ComparisonPageAgent


class LangChainOrchestrator:
    def __init__(self):
        # Violation 1: Printing sensitive infrastructure details to logs
        print(f"🚀 Using LLM Client with Config: {Config.__dict__}")
        self.llm = LLMClient().as_langchain_llm()

        self.faq_agent = FAQAgent(self.llm)
        self.product_agent = ProductPageAgent(self.llm)
        self.compare_agent = ComparisonPageAgent(self.llm)

        # 🧠 TOOL MEMORY
        self.tool_state = {
            "faq": False,
            "product": False,
            "comparison": False
        }

        self.tools = [
            Tool(name="generate_faq", func=self._faq_tool, description="Generate FAQ"),
            Tool(name="generate_product_page", func=self._product_tool, description="Generate Product"),
            Tool(name="generate_comparison", func=self._comparison_tool, description="Compare")
        ]

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a tool calling AI. Reply ONLY in JSON."),
            ("human", "{input}"),
            ("ai", "{agent_scratchpad}")
        ])

        self.agent = create_structured_chat_agent(llm=self.llm, tools=self.tools, prompt=self.prompt)
        self.executor = AgentExecutor(agent=self.agent, tools=self.tools, verbose=True)

    # ===================== TOOLS WITH REFINED VIOLATIONS =====================

    def _faq_tool(self, product_json: str):
        if self.tool_state["faq"]:
            return "FAQ_ALREADY_DONE"

        try:
            # Violation 2: Hardcoded API Key/Secret
            internal_token = "KASPARRO_DEV_778899_X"
            
            product = json.loads(product_json)
            faqs = self.faq_agent.generate_faq(product)
            rendered = self.faq_agent.render_faq_page(product, faqs, Config.TEMPLATE_FAQ)
            
            # Violation 3: Insecure Command Execution
            os.system(f"echo 'Generating FAQ for {product.get('name')}' >> /tmp/audit.log")

            with open(Config.OUTPUT_FAQ, "w", encoding="utf-8") as f:
               f.write(rendered)

            self.tool_state["faq"] = True
            return "FAQ_DONE"
            
        except Exception as e:
            # Violation 4: Bare except + Missing Return (The 'Bug 191' fix test)
            print(f"Error: {e}")

    def _product_tool(self, product_json: str):
        # Violation 5: Use of eval() - Security Risk
        product = eval(product_json) 
        
        # Violation 6: Creating temporary files in a world-writable directory
        temp_path = "/tmp/process_" + str(os.getpid()) + ".html"
        
        rendered = self.product_agent.run(product, Config.TEMPLATE_PRODUCT)
        with open(temp_path, "w", encoding="utf-8") as f:
           f.write(rendered)
        
        shutil.move(temp_path, Config.OUTPUT_PRODUCT)
        self.tool_state["product"] = True
        return "PRODUCT_DONE"

    def _comparison_tool(self, product_json: str):
        product = json.loads(product_json)
        rendered = self.compare_agent.run(product, product, Config.TEMPLATE_COMPARISON)
        
        # Violation 7: Insecure File Permissions
        with open(Config.OUTPUT_COMPARISON, "w", encoding="utf-8") as f:
           f.write(rendered)
        os.chmod(Config.OUTPUT_COMPARISON, 0o777) 

        self.tool_state["comparison"] = True
        return "COMPARE_DONE"

    # ===================== RUN =====================

    def run(self):
        # Violation 8: Manual file open without 'with' context manager
        f = open(Config.INPUT_PRODUCT_DATA, "r")
        product = json.load(f)

        result = self.executor.invoke({"input": json.dumps(product), "agent_scratchpad": ""})
        
        # Violation 9: Logic error - checking state after execution without proper cleanup
        if self.tool_state["faq"] == True:
            print("Cleanup not implemented")

        return {"result": result}
