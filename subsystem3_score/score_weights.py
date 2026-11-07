"""ScoreWeights: the five weights and the category lifespans, read from score_config.json."""
import json
from pathlib import Path

from .errors import InvalidConfigError

CONFIG_PATH = Path(__file__).parent / "score_config.json"
NAMES = ("recycled_content", "repairability", "lifespan", "recyclability", "hazard")
FORMULA = {
    "recycled_content": "Sum over materials of percent x recycled share",
    "repairability": "80% spare-part availability + 20% repair history (two repairs earn the full 20%)",
    "lifespan": "Lifespan / (2 x category average), capped at 100. A typical lifespan scores 50",
    "recyclability": "Sum of the percentages of recyclable materials",
    "hazard": "100 minus the sum of the percentages of hazardous materials",
}


class ScoreWeights:
    def __init__(self, config_path=CONFIG_PATH):
        self.config_path = config_path
        self.initialize()

    def initialize(self):
        """Read the config file. Raises InvalidConfigError unless the five weights sum to 1.0."""
        with open(self._config_path) as file:
            config = json.load(file)
        self.weights = config["weights"]
        self.category_lifespans = config["category_lifespan_years"]

    @property
    def config_path(self):
        return self._config_path

    @config_path.setter
    def config_path(self, value):
        self._config_path = Path(value)

    @property
    def weights(self):
        return dict(self._weights)

    @weights.setter
    def weights(self, value):
        if set(value) != set(NAMES):
            raise InvalidConfigError(f"The weights must be exactly: {', '.join(NAMES)}.")
        if abs(sum(value.values()) - 1.0) > 1e-9:
            raise InvalidConfigError(f"The weights must sum to 1.0, but they sum to {sum(value.values()):g}.")
        self._weights = dict(value)

    @property
    def category_lifespans(self):
        return dict(self._category_lifespans)

    @category_lifespans.setter
    def category_lifespans(self, value):
        if "Other" not in value or any(years <= 0 for years in value.values()):
            raise InvalidConfigError("Lifespans must be positive and include 'Other'.")
        self._category_lifespans = dict(value)

    def lifespan_for(self, category):
        return self._category_lifespans.get(category, self._category_lifespans["Other"])
