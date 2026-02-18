"""DeepEvalBaseLLM wrapper for vLLM and custom OpenAI-compatible providers.

Allows DeepEval judge metrics to use a self-hosted model endpoint
(e.g. vLLM, Ollama, Azure) instead of the default OpenAI endpoint.
"""

from __future__ import annotations

from typing import Any

from deepeval.models import DeepEvalBaseLLM
from openai import AsyncOpenAI


class CustomEvalLLM(DeepEvalBaseLLM):
    """DeepEval LLM wrapper for OpenAI-compatible endpoints."""

    def __init__(
        self,
        model_name: str,
        api_key: str,
        base_url: str | None = None,
    ) -> None:
        self._model_name = model_name
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )

    def get_model_name(self) -> str:
        return self._model_name

    def load_model(self) -> Any:
        return self._client

    async def a_generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate a response from the custom LLM."""
        response = await self._client.chat.completions.create(
            model=self._model_name,
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )
        return response.choices[0].message.content or ""

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Synchronous generation - required by DeepEval interface."""
        import asyncio

        return asyncio.get_event_loop().run_until_complete(
            self.a_generate(prompt, **kwargs)
        )
