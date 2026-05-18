"""LiteLLM-backed implementation of BaseAIService.

Wraps the litellm.completion / litellm.acompletion routes. Selected by the
AIService factory when AIConfig.provider == "litellm".
"""

from typing import Any, Optional, Tuple, Union

try:
    import litellm  # type: ignore[import-untyped]
except ImportError:
    litellm = None  # type: ignore[assignment]

from src.types.config import AIConfig

from .base import BaseAIService


class LiteLLMAIService(BaseAIService):
    def __init__(self, config: Union[AIConfig, None] = None) -> None:
        if litellm is None:
            raise ImportError(
                "litellm package is required for AI_PROVIDER=litellm. "
                "Install with: pip install litellm"
            )

        super().__init__(config)

        if self.config.base_url:
            litellm.api_base = self.config.base_url
        litellm.api_key = self.config.api_key

        litellm.context_window_fallback_dict = {
            "claude-sonnet-4-5": ["claude-sonnet-4", "claude-sonnet-4-20250514"],
            "glm-latest": ["claude-sonnet-4-5", "claude-sonnet-4-20250514"],
        }

    def generate(
        self, messages: Any, max_tokens: Optional[int] = None
    ) -> Tuple[str, bool, str]:
        try:
            if max_tokens is None:
                max_tokens = self.config.max_tokens

            completion_args = {
                "model": self.config.model_id,
                "messages": messages,
                "max_tokens": max_tokens,
                "api_key": self.config.api_key,
                "temperature": self.config.temperature,
            }
            if self.config.base_url:
                completion_args["api_base"] = self.config.base_url

            response = litellm.completion(**completion_args)
            result = response.choices[0].message["content"]
            if not result or not result.strip():
                return "", False, "No content generated"
            return result, True, ""

        except Exception as e:
            return "", False, str(e)

    async def vision_generate(
        self, messages: Any, max_tokens: Optional[int] = None
    ) -> Any:
        completion_args = {
            "model": self.config.vision_model_id,
            "messages": messages,
            "api_key": self.config.api_key,
            "temperature": 0.1,
        }
        if max_tokens is not None:
            completion_args["max_tokens"] = max_tokens
        if self.config.base_url:
            completion_args["api_base"] = self.config.base_url

        response = await litellm.acompletion(**completion_args)
        result = response.choices[0].message.content
        if not result or not result.strip():
            return ""
        return result
