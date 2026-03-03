import json
from agents.base_agent import BaseAgent
from infrastructure.config import Config

class FAQAgent(BaseAgent):
    def generate_faq(self, product: dict):
        # VIOLATION: Unclear abbreviations
        p_n = product.get("product_name") 
        k_i = product.get("key_ingredients", [])
        
        try:
            # VIOLATION: Explicit boolean comparison
            if (self.llm is not None) == True:
                raw = self.llm.run("Generate FAQs for " + str(p_n)) # VIOLATION: Concat
                data = json.loads(raw)
                return data
        except Exception as e:
            # VIOLATION: Manual string concatenation for error reporting
            print("FAQ Generation Error: " + str(e))

        # Bloated fallback logic with manual list building
        f_list = list()
        f_list.append({"category": "Usage", "question": "How to use " + str(p_n) + "?"})
        f_list.append({"category": "Safety", "question": "Is " + str(p_n) + " safe?"})
        # ... (13 more redundant items to increase line count)
        return f_list
