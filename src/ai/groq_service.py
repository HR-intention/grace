"""Groq-backed implementation of BaseAIService.

Talks to Groq's OpenAI-compatible /chat/completions endpoint via raw httpx.
No SDK dependency beyond httpx (which the project already uses for other
HTTP work). Selected by the AIService factory when AIConfig.provider == "groq".

Default endpoint: https://api.groq.com/openai/v1
Authentication: Bearer token from AIConfig.api_key.
"""

from typing import Any, Optional, Tuple, Union

import httpx

from src.types.config import AIConfig

from .base import BaseAIService

DEFAULT_GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_TIMEOUT_SECONDS = 120.0


class GroqAIService(BaseAIService):
    def __init__(self, config: Union[AIConfig, None] = None) -> None:
        super().__init__(config)

        if not self.config.api_key:
            raise ValueError(
                "AI_API_KEY is required for AI_PROVIDER=groq. "
                "Get one at https://console.groq.com/keys"
            )

        self._base_url = (
            self.config.base_url.rstrip("/")
            if self.config.base_url
            else DEFAULT_GROQ_BASE_URL
        )

        timeout = httpx.Timeout(DEFAULT_TIMEOUT_SECONDS)
        self._client = httpx.Client(timeout=timeout)
        self._async_client = httpx.AsyncClient(timeout=timeout)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

    def generate(
        self, messages: Any, max_tokens: Optional[int] = None
    ) -> Tuple[str, bool, str]:
        try:
            if max_tokens is None:
                max_tokens = self.config.max_tokens

            body: dict = {
                "model": self.config.model_id,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": self.config.temperature,
            }

            response = self._client.post(
                f"{self._base_url}/chat/completions",
                json=body,
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()

            choices = data.get("choices") or []
            if not choices:
                return "", False, "Groq response had no choices"
            content = choices[0].get("message", {}).get("content")
            if not content or not content.strip():
                return "", False, "No content generated"
            return content, True, ""

        except httpx.HTTPStatusError as e:
            body_preview = e.response.text[:500] if e.response is not None else ""
            return (
                "",
                False,
                f"Groq HTTP {e.response.status_code}: {body_preview}",
            )
        except httpx.RequestError as e:
            return "", False, f"Groq network error: {e}"
        except Exception as e:
            return "", False, str(e)

    async def vision_generate(
        self, messages: Any, max_tokens: Optional[int] = None
    ) -> Any:
        body: dict = {
            "model": self.config.vision_model_id,
            "messages": messages,
            "temperature": 0.1,
        }
        if max_tokens is not None:
            body["max_tokens"] = max_tokens

        response = await self._async_client.post(
            f"{self._base_url}/chat/completions",
            json=body,
            headers=self._headers(),
        )
        response.raise_for_status()
        data = response.json()

        choices = data.get("choices") or []
        if not choices:
            return ""
        content = choices[0].get("message", {}).get("content")
        if not content or not content.strip():
            return ""
        return content

    def __del__(self) -> None:
        try:
            self._client.close()
        except Exception:
            pass
