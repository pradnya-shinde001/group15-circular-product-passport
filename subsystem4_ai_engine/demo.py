"""Shows the four Subsystem 4 classes.  Run:  python -m subsystem4_ai_engine.demo"""
from .ai_prediction import AIPrediction
from .llm_adapter import LLMAdapter
from .recommender import Recommender
from .rule_based_advisor import RuleBasedAdvisor

PRODUCT = {"name": "ThinkPad Laptop", "condition": "Good", "repairability_score": 60, "reusability_score": 72}


def main():
    print("1. AIPrediction")
    prediction = AIPrediction("Repair", "Sample reason.", "demo")
    print("   Action:", prediction.get_action())
    prediction.set_action("Reuse")
    print("   Updated action:", prediction.get_action())
    print("   Created at, set by initialize():", prediction.get_created_at())

    print("2. RuleBasedAdvisor")
    advisor = RuleBasedAdvisor()
    print("   Resale minimum:", advisor.get_resale_minimum())
    advisor.set_resale_minimum(70)
    print("   Updated resale minimum:", advisor.get_resale_minimum())
    print("   Actions, set by initialize():", advisor.get_actions())

    print("3. LLMAdapter")
    adapter = LLMAdapter()
    print("   Max tokens:", adapter.get_max_tokens())
    adapter.set_max_tokens(300)
    print("   Updated max tokens:", adapter.get_max_tokens())
    print("   API key found by initialize():", adapter.has_api_key())

    print("4. Recommender")
    recommender = Recommender(adapter)
    print("   Advisor, set by initialize():", type(recommender.get_advisor()).__name__)
    recommender.set_advisor(advisor)
    print("   Product:", PRODUCT["name"])
    result = recommender.recommend(PRODUCT)
    print("   Recommended action:", result.get_action())
    print("   Reason:", result.get_reason())
    print("   Answered by:", result.get_source())


if __name__ == "__main__":
    main()
