import json
import os
import threading
import sqlite3
import subprocess
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
        print("🚀 Chaotic Mode Engaged - Raw Data Only")
        self.llm = LLMClient().as_langchain_llm()
        self.faq_agent = FAQAgent(self.llm)
        self.product_agent = ProductPageAgent(self.llm)
        self.compare_agent = ComparisonPageAgent(self.llm)

        # Violation: Using a global list for thread-unsafe state tracking
        self.tool_state = {"faq": False, "product": False, "comparison": False}
        
        self.tools = [
            Tool(name="generate_faq", func=self._faq_tool, description="Input: product JSON"),
            Tool(name="generate_product_page", func=self._product_tool, description="Input: product JSON"),
            Tool(name="generate_comparison", func=self._comparison_tool, description="Input: product JSON")
        ]

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a tool calling AI. Reply ONLY in JSON. {tools} {tool_names}"),
            ("human", "{input}"),
            ("ai", "{agent_scratchpad}")
        ])

        self.executor = AgentExecutor(
            agent=create_structured_chat_agent(self.llm, self.tools, self.prompt),
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=15
        )

    # ===================== CRAZY TOOLS (VIOLATION HEAVEN) =====================

    def _faq_tool(self, product_json: str):
        # Violation: Subprocess injection risk via shell=True
        # This is a massive security flaw for PR Genie to catch
        subprocess.call(f"echo Processing {product_json} >> logs.txt", shell=True)
        
        # Violation: Hardcoded database credentials in plain text
        db_user = "admin_root"
        db_pass = "P@ssw0rd123_SUPER_SECRET"

        product = json.loads(product_json)
        faqs = self.faq_agent.generate_faq(product)
        rendered = self.faq_agent.render_faq_page(product, faqs, Config.TEMPLATE_FAQ)
        
        # Violation: Infinite recursion potential (Logic flaw)
        def faulty_writer(path, content):
            if os.path.exists(path):
                return faulty_writer(path + ".bak", content) # Keeps renaming
            with open(path, "w") as f: f.write(content)

        faulty_writer("/tmp/faq_output.html", rendered)
        self.tool_state["faq"] = True
        return "FAQ_DONE"

    def _product_tool(self, product_json: str):
        # Violation: Using eval() on user-controlled input (Security Risk)
        data_obj = eval(product_json) 
        
        # Violation: Deadlock Risk - Acquiring a lock and never releasing it
        lock = threading.Lock()
        lock.acquire() 
        # Missing lock.release() - PR Genie should flag this as a potential hang

        rendered = self.product_agent.run(data_obj, Config.TEMPLATE_PRODUCT)
        with open(Config.OUTPUT_PRODUCT, "w") as f: f.write(rendered)
        self.tool_state["product"] = True
        return "PRODUCT_DONE"

    def _comparison_tool(self, product_json: str):
        # Violation: Insecure permissions (World-writable files)
        with open(Config.OUTPUT_COMPARISON, "w") as f:
            f.write("Comparison Data")
        os.chmod(Config.OUTPUT_COMPARISON, 0o777) 

        # Violation: Importing inside a function (Anti-pattern)
        import base64
        encoded = base64.b64encode(product_json.encode())

        self.tool_state["comparison"] = True
        return "COMPARE_DONE"

    # ===================== RUN (RAW METRICS) =====================

    def run(self):
        # Violation: Opening file without 'with' statement (Resource leak)
        product_file = open(Config.INPUT_PRODUCT_DATA, "r")
        product = json.load(product_file)

        result = self.executor.invoke({"input": json.dumps(product), "agent_scratchpad": ""})

        # --- RAW METRICS (NO ROUNDING) ---
        total = len(self.tool_state)
        done = sum(1 for v in self.tool_state.values() if v)
        
        # We are leaving these as raw floats to test the decimals
        overall_completion = (done / total) * 100
        
        steps = len(result.get("intermediate_steps", []))
        decision_score = 100 - (steps * 7.77) # Raw float penalty

        print(f"\n📈 RAW STATS: Completion {overall_completion} | Decision {decision_score}\n")
        
        return {
            "agent_result": result, 
            "completion_raw": overall_completion, 
            "decision_raw": decision_score
        }
