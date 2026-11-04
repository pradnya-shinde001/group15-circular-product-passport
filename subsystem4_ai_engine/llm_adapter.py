"""The one place that talks to an LLM. Changing provider means changing only this module.

All providers speak the OpenAI "chat/completions" format, so no vendor SDK is needed.
API keys are read from environment variables only.
"""
import os

import requests

MAX_OUTPUT_TOKENS = 500

# Model names change over time - pass another one to LLMAdapter(provider, model).
PROVIDERS = {
    "Offline (no API key)": {"base_url": None, "model": None, "env": None,
                              "help": "Rule-based explanation. No internet needed."},
    "KI:connect.NRW (college)": {"base_url": "https://chat.kiconnect.nrw/api/v1",
                                  "model": "GPT-OSS-120B", "env": "KICONNECT_API_KEY",
                                  "help": "Key: https://chat.kiconnect.nrw > your name (bottom left) > API key "
                                          "management. Keys expire after a month without login. "
                                          "Use the model name exactly as listed by GET /models."},
    "Groq (free tier)": {"base_url": "https://api.groq.com/openai/v1",
                          "model": "llama-3.3-70b-versatile", "env": "GROQ_API_KEY",
                          "help": "Free key: https://console.groq.com/keys"},
    "Google Gemini (free tier)": {"base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
                                   "model": "gemini-3.8-flash", "env": "GEMINI_API_KEY",
                                   "help": "Free key: https://aistudio.google.com/apikey"},
    "OpenAI (paid)": {"base_url": "https://api.openai.com/v1",
                       "model": "gpt-4o-mini", "env": "OPENAI_API_KEY",
                       "help": "Key: https://platform.openai.com/api-keys"},
    "OpenRouter (free models)": {"base_url": "https://openrouter.ai/api/v1",
                                  "model": "meta-llama/llama-3.3-70b-instruct:free",
                                  "env": "OPENROUTER_API_KEY",
                                  "help": "Free key: https://openrouter.ai/keys"},
}


class LLMError(Exception):
    pass


class LLMAdapter:
    def __init__(self, provider, model=None, max_tokens=MAX_OUTPUT_TOKENS):
        self._provider = None
        self._model = model
        self.max_tokens = max_tokens
        # Filled in by complete() from the API response, for prediction logging.
        self._last_model = None
        self._last_version = "unknown"
        self._last_finish_reason = None
        self.provider = provider  # the setter calls initialize()

    def initialize(self):
        """Load the provider's settings and read its API key from the environment."""
        cfg = PROVIDERS[self._provider]
        self._base_url = cfg["base_url"]
        self._env = cfg["env"]
        self._model = self._model or cfg["model"]
        # Requirement: the key lives only in an environment variable, so it has no getter or setter.
        self._api_key = os.environ.get(self._env, "") if self._env else ""
        self._last_model = self._model

    @property
    def provider(self):
        return self._provider

    @provider.setter
    def provider(self, value):
        if value not in PROVIDERS:
            raise ValueError(f"provider must be one of {list(PROVIDERS)}.")
        if self._provider is not None and value != self._provider:
            self._model = None  # a model name only makes sense for its own provider
        self._provider = value
        self.initialize()

    @property
    def model(self):
        return self._model

    @model.setter
    def model(self, value):
        if not value:
            raise ValueError("model is required.")
        self._model = value
        self._last_model = value

    @property
    def max_tokens(self):
        return self._max_tokens

    @max_tokens.setter
    def max_tokens(self, value):
        if not 1 <= value <= MAX_OUTPUT_TOKENS:
            raise ValueError(f"max_tokens must be 1 to {MAX_OUTPUT_TOKENS} (requirement: limit LLM output).")
        self._max_tokens = value

    @property
    def base_url(self):
        return self._base_url

    @property
    def has_api_key(self):
        return bool(self._api_key)

    @property
    def last_model(self):
        return self._last_model

    @property
    def last_version(self):
        return self._last_version

    @property
    def last_finish_reason(self):
        """'length' means the answer was cut off at the token limit."""
        return self._last_finish_reason

    def complete(self, prompt, system=(), history=(), timeout=40):
        """Send one user prompt and return the answer text. Raises LLMError on any failure."""
        if not self._base_url:
            raise LLMError(f"{self._provider} has no LLM.")
        if not self._api_key:
            raise LLMError(f"No API key for {self._provider}. Set the {self._env} environment variable "
                           "and run again.")

        messages = [{"role": "system", "content": s} for s in system]
        messages += [{"role": m["role"], "content": m["content"]} for m in history]
        messages.append({"role": "user", "content": prompt})

        try:
            r = requests.post(
                self._base_url.rstrip("/") + "/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
                json={"model": self._model, "messages": messages,
                      "temperature": 0.3, "max_tokens": self._max_tokens},
                timeout=timeout,
            )
            if r.status_code != 200:
                hint = ""
                if r.status_code in (400, 404):
                    hint = (" Hint: the model name may be retired - pass the "
                            "one named in the provider's error or docs.")
                raise LLMError(f"{self._provider} returned HTTP {r.status_code}: {r.text[:300]}{hint}")
            data = r.json()
            text = (data["choices"][0]["message"]["content"] or "").strip()
            if not text:
                raise LLMError(f"{self._provider} returned an empty answer "
                               f"(finish reason: {data['choices'][0].get('finish_reason')}).")
        except requests.RequestException as e:
            raise LLMError(f"Network error: {e}") from e
        except (KeyError, IndexError, TypeError, ValueError, AttributeError) as e:
            raise LLMError(f"Unexpected API response: {e}") from e

        self._last_model = data.get("model") or self._model
        self._last_finish_reason = data["choices"][0].get("finish_reason")
        self._last_version = data.get("system_fingerprint") or self._last_model
        return text
