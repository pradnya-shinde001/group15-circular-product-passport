"""RuleBasedAdvisor: chooses an action using simple fixed rules."""


class RuleBasedAdvisor:
    def __init__(self, resale_minimum=60, repair_minimum=60):
        self._resale_minimum = resale_minimum
        self._repair_minimum = repair_minimum
        self._actions = []
        self.initialize()

    def initialize(self):
        """Set the actions that can be recommended."""
        self._actions = ["Repair", "Resale", "Reuse", "Recycling"]

    def get_resale_minimum(self):
        return self._resale_minimum

    def set_resale_minimum(self, resale_minimum):
        self._resale_minimum = resale_minimum

    def get_repair_minimum(self):
        return self._repair_minimum

    def set_repair_minimum(self, repair_minimum):
        self._repair_minimum = repair_minimum

    def get_actions(self):
        return self._actions

    def set_actions(self, actions):
        self._actions = actions

    def advise(self, product):
        """Return the action and the reason for one product."""
        condition = product["condition"]
        reusability = product["reusability_score"]
        repairability = product["repairability_score"]

        good_condition = condition in ("Excellent", "Good")

        if good_condition and reusability >= self._resale_minimum:
            return "Resale", f"Condition is {condition} and reusability is {reusability}."
        if good_condition:
            return "Reuse", f"Condition is {condition} but reusability is only {reusability}."
        if repairability >= self._repair_minimum:
            return "Repair", f"Condition is {condition} but repairability is {repairability}."
        return "Recycling", f"Condition is {condition} and repairability is only {repairability}."
