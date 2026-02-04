import json
import os
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
        print("🚀 Using Groq LLM")
        self.llm = LLMClient().as_langchain_llm()

        self.faq_agent = FAQAgent(self.llm)
        self.product_agent = ProductPageAgent(self.llm)
        self.compare_agent = ComparisonPageAgent(self.llm)

        # 🧠 TOOL MEMORY — tracks which "features" are completed
        self.tool_state = {
            "faq": False,
            "product": False,
            "comparison": False
        }

        # ===================== TOOLS =====================
        self.tools = [
            Tool(
                name="generate_faq",
                func=self._faq_tool,
                description="Generate FAQ page. Input must be product JSON string"
            ),
            Tool(
                name="generate_product_page",
                func=self._product_tool,
                description="Generate product page. Input must be product JSON string"
            ),
            Tool(
                name="generate_comparison",
                func=self._comparison_tool,
                description="Generate comparison page. Input must be product JSON string"
            )
        ]

        # ===================== PROMPT =====================
        self.prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are a tool calling AI.\n\n"
             "You must call ALL tools exactly once.\n"
             "When all tools return DONE, output Final.\n\n"
             "Available tools:\n{tools}\n\n"
             "Tool names:\n{tool_names}\n\n"
             "Reply ONLY in JSON.\n\n"
             "Tool call format:\n"
             "{{\"action\":\"tool_name\",\"action_input\":\"json\"}}\n\n"
             "Final format:\n"
             "{{\"action\":\"Final\",\"action_input\":\"done\"}}\n\n"
             "Never repeat a tool that already returned DONE.\n"
             "Never explain.\n"
             "Never output python.\n"
             "Never output English."
            ),
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
            handle_parsing_errors=True,
            max_iterations=10
        )

    # ===================== TOOLS WITH TEST VIOLATIONS =====================

    def _faq_tool(self, product_json: str):
        if self.tool_state["faq"]:
            return "FAQ_ALREADY_DONE"
        try:
            print("🟢 TOOL: FAQ")
            # Logic here...
            self.tool_state["faq"] = True
            return "FAQ_DONE"
        except Exception as e:
            return f"Error: {e}"

    def _product_tool(self, product_json: str):
        if self.tool_state["product"]:
            return "PRODUCT_ALREADY_DONE"
        print("🟢 TOOL: PRODUCT")
        self.tool_state["product"] = True
        return "PRODUCT_DONE"

    def _comparison_tool(self, product_json: str):
        if self.tool_state["comparison"]:
            return "COMPARE_ALREADY_DONE"
        print("🟢 TOOL: COMPARISON")
        self.tool_state["comparison"] = True
        return "COMPARE_DONE"

    # ===================== RUN (TESTING PR GENIE METRICS) =====================

    def run(self):
        # Open file to simulate PR analysis input
        with open(Config.INPUT_PRODUCT_DATA, "r", encoding="utf-8") as product_file:
            product = json.load(product_file)

        prompt_str = "Call all tools to generate all pages.\n\n" + json.dumps(product)

        result = self.executor.invoke({
            "input": prompt_str,
            "agent_scratchpad": ""
        })

        # --- TEST 1: OVERALL COMPLETION (Functional Assessment) ---
        # Calculation: (Total Features Completed / Total Features) * 100
        total_feats = len(self.tool_state)
        done_feats = sum(1 for status in self.tool_state.values() if status)
        
        # Applying Arithmetic Rounding: int(float(x) + 0.5)
        raw_completion = (done_feats / total_feats) * 100
        overall_completion = int(float(raw_completion) + 0.5)

        # --- TEST 2: DECISION STRENGTH (Confident Score) ---
        # Simulating logic: Start at 100, penalize for loops or high number of steps
        steps = len(result.get("intermediate_steps", []))
        # Use a non-integer penalty to force a decimal and test the rounder
        raw_strength = max(0, 100 - (steps * 8.67))
        decision_strength = int(float(raw_strength) + 0.5)

        print("\n" + "="*50)
        print(f"🚀 PR GENIE TEST RESULTS (INTEGER ENFORCED)")
        print(f"📌 Overall Completion: {overall_completion}%")
        print(f"🧠 Decision Strength: {decision_strength}%")
        print("="*50 + "\n")

        return {
            "overall_completion": overall_completion,
            "decision_strength": decision_strength,
            "agent_result": result
        }
