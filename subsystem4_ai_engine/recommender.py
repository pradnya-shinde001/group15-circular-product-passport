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
        answer = self._ask_llm(product)
        if answer is not None:
            action, reason = answer
            return AIPrediction(action, reason, "llm", model=self._adapter.get_model())

        action, reason = self._advisor.advise(product)
        return AIPrediction(action, reason, "rules", model=self._advisor.get_version())

    def _ask_llm(self, product):
        """Return the LLM's (action, reason), or None if there is no usable answer."""
        if self._adapter is None or not self._adapter.has_api_key():
            return None

        actions = self._advisor.get_actions()
        question = (f"Product: {product}\n"
                    f"Choose one action for this product: {actions}.\n"
                    f"Give one short reason that uses the product data.\n"
                    f"Reply with one line only, in this form:  Action: reason")
        try:
            answer = self._adapter.ask(question)
        except LLMError:
            return None  # the LLM could not answer, so the rules will

        # Keep only the first line, then split it:
        # "Repair: The battery is weak." -> action "Repair", reason "The battery is weak."
        first_line = answer.strip().splitlines()[0] if answer.strip() else ""
        action, _, reason = first_line.partition(":")
        action = action.strip(" *")
        reason = reason.strip()
        if action not in actions:
            return None
        if reason == "":
            _, reason = self._advisor.advise(product)  # the LLM gave no reason, so the rules give one
        return action, reason
