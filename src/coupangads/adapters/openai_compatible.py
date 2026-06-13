"""Generic OpenAI-compatible text adapter.

Supports any provider that exposes an OpenAI-compatible chat completions API,
such as DeepSeek, Moonshot/Kimi, MiniMax, OpenAI, etc.
"""

from openai import OpenAI

from coupangads.adapters.base import TextAdapter
from coupangads.core import config


class OpenAICompatibleTextAdapter(TextAdapter):
    """Text-only adapter for OpenAI-compatible endpoints."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        max_retries: int = config.DEFAULT_MAX_RETRIES,
        request_timeout: int = config.DEFAULT_REQUEST_TIMEOUT_MS,
    ) -> None:
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            max_retries=max_retries,
            timeout=request_timeout,
        )
        self.model = model
        self._messages: list[dict] = []

    def chat(self, prompt: str) -> str:
        """Send a text request and return the model response."""
        self._messages.append({"role": "user", "content": prompt})
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self._messages,
        )
        content = response.choices[0].message.content or ""
        self._messages.append({"role": "assistant", "content": content})
        return content
