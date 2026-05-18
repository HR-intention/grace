"""Base AI service contract.

Defines the abstract interface every provider implementation must satisfy
(generate, vision_generate) plus the shared higher-level helpers
(generate_tech_spec, get_file_name, generate_mock_server) which are
provider-agnostic — they just call self.generate().
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, List, Optional, Tuple, Union

from src.config import get_config
from src.types.config import AIConfig
from src.utils.ai_utils import combine_markdown_files

from .system.prompt_config import prompt_config


class BaseAIService(ABC):
    """Abstract base class. Subclasses implement generate / vision_generate per provider.

    All callsites construct via the AIService factory in src.ai.ai_service,
    which returns the right concrete subclass based on AIConfig.provider.
    """

    config: AIConfig

    def __init__(self, config: Union[AIConfig, None] = None) -> None:
        self.config = config or get_config().getAiConfig()

    # ------------------------------------------------------------------
    # Provider-specific (abstract)
    # ------------------------------------------------------------------

    @abstractmethod
    def generate(
        self, messages: Any, max_tokens: Optional[int] = None
    ) -> Tuple[str, bool, str]:
        """Sync chat completion.

        Returns (text, success, error_message). On success, error_message is "".
        On failure, text is "" and error_message describes the failure.
        """

    @abstractmethod
    async def vision_generate(
        self, messages: Any, max_tokens: Optional[int] = None
    ) -> Any:
        """Async vision/multimodal completion. Returns the response text or ""."""

    # ------------------------------------------------------------------
    # Shared higher-level helpers (call self.generate)
    # ------------------------------------------------------------------

    def generate_tech_spec(
        self, filemanager, markdown_files: List[Path]
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Generate a technical specification from markdown source documents.

        Chunks large inputs into ~80k-token windows, generates per chunk,
        then optionally merges results. Returns (success, spec, error).
        """
        try:
            from src.utils.ai_utils import chunk_content_by_tokens, estimate_tokens

            combined_content: List[str] = combine_markdown_files(
                filemanager, markdown_files
            )
            if not combined_content or len(combined_content) == 0:
                return False, "", "No content found in markdown files"

            pages = [
                {"url": f"file_{i}", "content": content}
                for i, content in enumerate(combined_content)
            ]

            total_tokens = sum(estimate_tokens(page["content"]) for page in pages)
            print(f"Total content: ~{total_tokens:,} tokens from {len(pages)} pages")

            chunks = chunk_content_by_tokens(pages, max_tokens_per_chunk=80000)
            print(f"Split into {len(chunks)} chunks")

            prompt = (
                prompt_config().get_with_values(
                    "techspecPrompt", {"content": "check in user message"}
                )
                or ""
            )

            chunk_results = []
            for i, chunk in enumerate(chunks):
                chunk_tokens = sum(estimate_tokens(page["content"]) for page in chunk)
                prompt_tokens = estimate_tokens(prompt)
                safe_max_tokens = min(
                    16384, max(4096, 200000 - chunk_tokens - prompt_tokens - 10000)
                )

                print(
                    f"Processing chunk {i + 1}/{len(chunks)} "
                    f"(~{chunk_tokens:,} tokens, max_output: {safe_max_tokens})..."
                )

                chunk_content_parts = [
                    f"--- Document {j + 1} ---\n{page['content']}"
                    for j, page in enumerate(chunk)
                ]
                combined_chunk_content = "\n\n".join(chunk_content_parts)

                messages = [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": combined_chunk_content},
                ]

                tech_spec, success, error = self.generate(
                    messages, max_tokens=safe_max_tokens
                )
                if not success:
                    if chunk_results:
                        print(
                            f"Warning: Chunk {i + 1} failed, returning partial results"
                        )
                        return True, "\n\n".join(chunk_results), None
                    return False, None, error

                chunk_results.append(tech_spec)

            if len(chunk_results) > 1:
                total_result_tokens = sum(
                    estimate_tokens(result) for result in chunk_results
                )

                if total_result_tokens > 60000:
                    print(
                        f"Combined results too large (~{total_result_tokens:,} tokens), "
                        f"concatenating {len(chunk_results)} chunks directly..."
                    )
                    return True, "\n\n".join(chunk_results), None

                combine_prompt = """You are a technical writer. Your task is to combine multiple parts of a technical specification into a single cohesive document.

Instructions:
1. Merge all parts into a unified document
2. Remove any duplicate information
3. Ensure consistency in terminology and formatting
4. Maintain all crucial technical details from each part
5. Organize the content logically"""

                combined_parts = [
                    f"--- Part {i + 1} of {len(chunk_results)} ---\n{result}"
                    for i, result in enumerate(chunk_results)
                ]

                combine_tokens = sum(
                    estimate_tokens(part) for part in combined_parts
                ) + estimate_tokens(combine_prompt)

                safe_combine_max = min(
                    32768, max(16384, 200000 - combine_tokens - 10000)
                )

                print(
                    f"Combining {len(chunk_results)} chunks "
                    f"(~{combine_tokens:,} tokens, max_output: {safe_combine_max})..."
                )

                combined_content_str = "\n\n".join(combined_parts)
                messages = [
                    {"role": "system", "content": combine_prompt},
                    {"role": "user", "content": combined_content_str},
                ]
                final_spec, success, error = self.generate(
                    messages, max_tokens=safe_combine_max
                )
                if not success:
                    print(
                        "Warning: Could not combine chunks, returning concatenated results"
                    )
                    return True, "\n\n".join(chunk_results), None
                return True, final_spec, None

            return True, chunk_results[0], None

        except Exception as e:
            return False, None, str(e)

    def get_file_name(
        self, tech_spec: str, connector: bool = True, base_name: str = "tech_spec"
    ) -> str:
        """Ask the LLM for a short filename derived from the spec content."""
        try:
            truncated_spec = tech_spec[:2000] if len(tech_spec) > 2000 else tech_spec

            prompt = (
                prompt_config().get_with_values(
                    "techspecFileNamePrompt",
                    {"tech_spec": truncated_spec or ""},
                )
                or ""
            )
            name = self.generate([{"role": "user", "content": prompt}], max_tokens=20)
            cleaned_name = name[0].strip().split("\n")[0].split(".")[0]
            cleaned_name = cleaned_name.strip("\"'` ").replace(" ", "")
            cleaned_name = (
                cleaned_name.replace("/", "").replace("\\", "").replace(":", "")
            )
            if len(cleaned_name) > 40:
                cleaned_name = base_name
            return cleaned_name if cleaned_name else base_name
        except Exception:
            return base_name

    def generate_mock_server(
        self, tech_spec: str
    ) -> Tuple[bool, Optional[dict], Optional[str]]:
        """Generate a mock-server payload from a tech spec via the LLM."""
        try:
            prompt = (
                prompt_config().get_with_values(
                    "techspecMockServerPrompt", {"tech_spec": tech_spec or ""}
                )
                or ""
            )
            messages = [{"role": "user", "content": prompt}]
            response, success, error = self.generate(messages)
            if not success:
                return False, None, error
            return True, response, None
        except Exception as e:
            return False, None, str(e)
