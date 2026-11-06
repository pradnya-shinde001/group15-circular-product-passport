"""LLMAdapter: sends a question to the LLM and returns its answer."""
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

from .errors import LLMError

load_dotenv(Path(__file__).parent.parent / ".env")


class LLMAdapter:
    def __init__(self, model="GPT-OSS-120B", max_tokens=500):
        self._url = "https://chat.kiconnect.nrw/api/v1/chat/completions"
        self._model = model
        self._max_tokens = max_tokens
        self._api_key = ""
        self.initialize()

    def initialize(self):
        """Read the API key from the .env file or the environment."""
        self._api_key = os.environ.get("KICONNECT_API_KEY", "")

    def get_url(self):
        return self._url

    def set_url(self, url):
        self._url = url

    def get_model(self):
        return self._model

    def set_model(self, model):
        self._model = model

    def get_max_tokens(self):
        return self._max_tokens

    def set_max_tokens(self, max_tokens):
        self._max_tokens = max_tokens

    def has_api_key(self):
        return self._api_key != ""

    def ask(self, question):
        """Send the question to the LLM and return its answer.
        Raises LLMError when there is no key, no connection, or an answer in an unexpected format."""
        if not self.has_api_key():
            raise LLMError("No API key is set.")

        try:
            response = requests.post(
                self._url,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={"model": self._model,
                      "max_tokens": self._max_tokens,
                      "messages": [{"role": "user", "content": question}]},
                timeout=8,
            )
            response.raise_for_status()
        except requests.RequestException as error:  # no internet, timeout, or an error status such as 401
            raise LLMError(f"The LLM could not be reached: {type(error).__name__}.") from error

        try:
            return response.json()["choices"][0]["message"]["content"].strip()
        except (ValueError, KeyError, IndexError, TypeError, AttributeError) as error:
            raise LLMError("The LLM sent an answer in an unexpected format.") from error
