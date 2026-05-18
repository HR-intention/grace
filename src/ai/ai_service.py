"""AIService factory.

Returns the concrete BaseAIService implementation selected by
AIConfig.provider. Callers continue to use:

    from src.ai.ai_service import AIService
    service = AIService(ai_config)
    text, ok, err = service.generate(messages)

The factory is a plain function (not a class) but kept under the
historical name `AIService` so existing callsites don't need to change.

Provider selection:
- "groq"    -> GroqAIService (raw httpx, OpenAI-compatible endpoint)
- "litellm" -> LiteLLMAIService (wraps the litellm package)

Default when AIConfig.provider is empty/None: "groq".
"""

from typing import Union

from src.config import get_config
from src.types.config import AIConfig

from .base import BaseAIService


def AIService(config: Union[AIConfig, None] = None) -> BaseAIService:
    """Return the configured AI service implementation.

    Backwards-compatible name: callers can still write `AIService(cfg)`
    and get an instance back, even though this is a function and not
    a class.
    """
    cfg = config or get_config().getAiConfig()
    provider = (cfg.provider or "groq").strip().lower()

    if provider == "groq":
        from .groq_service import GroqAIService

        return GroqAIService(cfg)

    if provider == "litellm":
        from .litellm_service import LiteLLMAIService

        return LiteLLMAIService(cfg)

    raise ValueError(
        f"Unknown AI_PROVIDER {provider!r}. Expected one of: 'groq', 'litellm'."
    )


__all__ = ["AIService", "BaseAIService"]
