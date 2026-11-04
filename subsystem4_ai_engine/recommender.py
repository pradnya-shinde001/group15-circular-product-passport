"""End-of-life recommendation: the LLM decides, and RuleBasedAdvisor takes over when it cannot."""
import json
import re

from .ai_prediction import AIPrediction
from .llm_adapter import LLMAdapter, LLMError
from .rule_based_advisor import RuleBasedAdvisor, product_facts

ACTIONS = ["Repair", "Resale", "Reuse", "Recycling"]

# (connect, read) seconds, so that the fallback still answers within the 10 s limit.
LLM_TIMEOUT = (2, 7.5)

SYSTEM_PROMPT = f"""You advise on the end of life of one electronic product.
Choose exactly one action: {", ".join(ACTIONS)}.
Use only the facts in the product JSON and never invent any.
The reason must quote at least two values from the JSON and be under 60 words.
Reply with JSON only: {{"action": "<action>", "reason": "<reason>"}}"""


class Recommender:
    def __init__(self, adapter=None, advisor=None, timeout=LLM_TIMEOUT):
        self._adapter = None
        self._advisor = None
        self._reason = None
        self.timeout = timeout
        self.initialize(adapter, advisor)

    def initialize(self, adapter=None, advisor=None):
        """Connect the collaborators. Without an adapter, every answer comes from the rules."""
        self.adapter = adapter
        self.advisor = advisor or RuleBasedAdvisor()

    @property
    def adapter(self):
        return self._adapter

    @adapter.setter
    def adapter(self, value):
        if value is not None and not isinstance(value, LLMAdapter):
            raise TypeError("adapter must be an LLMAdapter or None.")
        self._adapter = value

    @property
    def advisor(self):
        return self._advisor

    @advisor.setter
    def advisor(self, value):
        if not isinstance(value, RuleBasedAdvisor):
            raise TypeError("advisor must be a RuleBasedAdvisor.")
        self._advisor = value

    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self, value):
        # (connect, read) seconds. The requirement is an answer in under 10 s, including the fallback.
        if len(value) != 2 or sum(value) >= 10:
            raise ValueError("timeout must be (connect, read) seconds adding up to under 10.")
        self._timeout = tuple(value)

    @property
    def reason(self):
        """Read-only: the reason given by the latest recommendation."""
        return self._reason

    def recommend(self, product, circularity_score=None):
        """Return an AIPrediction whose result holds action, reason and source."""
        pid = product["product_id"]
        fallback_reason = "No LLM selected."
        if self._adapter is not None:
            try:
                facts = product_facts(product, circularity_score)
                text = self._adapter.complete("Product JSON:\n" + json.dumps(facts, indent=1) + "\nAnswer with the JSON object only.",
                                              system=[SYSTEM_PROMPT], timeout=self._timeout)
                action, reason = self._parse(text)
                self._reason = reason
                return AIPrediction("recommendation", {"action": action, "reason": reason, "source": "llm"},
                                    self._adapter.last_model, self._adapter.last_version, pid)
            except (LLMError, ValueError) as e:
                fallback_reason = str(e)

        action, reason = self._advisor.advise(product)
        self._reason = reason
        return AIPrediction("recommendation",
                            {"action": action, "reason": reason, "source": "rules",
                             "fallback_reason": fallback_reason},
                            RuleBasedAdvisor.MODEL_NAME, RuleBasedAdvisor.VERSION, pid)

    @staticmethod
    def _parse(text):
        """Models sometimes wrap JSON in text or code fences. Raises ValueError if it is unusable."""
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            raise ValueError(f"The LLM did not return JSON. It said: {text[:200]}")
        data = json.loads(match.group())
        if not isinstance(data, dict):
            raise ValueError(f"The LLM did not return a JSON object. It said: {text[:200]}")
        action = str(data.get("action", "")).strip().capitalize()
        reason = str(data.get("reason", "")).strip()
        if action not in ACTIONS or not reason:
            raise ValueError(f"The LLM returned an unusable recommendation: {text[:200]}")
        return action, reason
