"""Recommender: asks the LLM first and uses the rules if the LLM cannot answer."""
from .ai_prediction import AIPrediction
from .errors import LLMError
from .rule_based_advisor import RuleBasedAdvisor


class Recommender:
    def __init__(self, adapter=None):
        self._adapter = adapter
        self._advisor = None
        self.initialize()

    def initialize(self):
        """Create the advisor that gives the backup answer."""
        self._advisor = RuleBasedAdvisor()

    def get_adapter(self):
        return self._adapter

    def set_adapter(self, adapter):
        self._adapter = adapter

    def get_advisor(self):
        return self._advisor

    def set_advisor(self, advisor):
        self._advisor = advisor

    def recommend(self, product):
        """Return an AIPrediction for one product."""
        action = self._ask_llm(product)
        if action is not None:
            return AIPrediction(action, "Chosen by the LLM.", "llm")

        action, reason = self._advisor.advise(product)
        return AIPrediction(action, reason, "rules")

    def _ask_llm(self, product):
        """Return the LLM's action, or None if there is no usable answer."""
        if self._adapter is None or not self._adapter.has_api_key():
            return None

        actions = self._advisor.get_actions()
        question = f"Choose one action for this product: {actions}. Reply with one word only. Product: {product}"
        try:
            answer = self._adapter.ask(question)
        except LLMError:
            return None  # the LLM could not answer, so the rules will

        return answer if answer in actions else None
