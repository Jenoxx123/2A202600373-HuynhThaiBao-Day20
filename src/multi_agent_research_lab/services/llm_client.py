"""LLM client abstraction.

Production note: agents should depend on this interface instead of importing an SDK directly.
"""

from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from tenacity import RetryError, retry, stop_after_attempt, wait_exponential

from multi_agent_research_lab.core.config import Settings, get_settings


@dataclass(frozen=True)
class LLMResponse:
    content: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None


class LLMClient:
    """Provider-agnostic LLM client with OpenAI + deterministic fallback."""

    _provider_disabled: bool = False

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Return a model completion with graceful fallback."""

        if LLMClient._provider_disabled:
            return self._fallback_response(user_prompt, reason="provider_disabled")
        if not self.settings.openai_api_key:
            return self._fallback_response(user_prompt, reason="missing_openai_api_key")
        try:
            return self._complete_with_openai(system_prompt=system_prompt, user_prompt=user_prompt)
        except RetryError:
            LLMClient._provider_disabled = True
            return self._fallback_response(user_prompt, reason="openai_retry_exhausted")
        except Exception:
            LLMClient._provider_disabled = True
            return self._fallback_response(user_prompt, reason="openai_unavailable")

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def _complete_with_openai(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        from openai import OpenAI

        timeout_seconds = float(min(self.settings.timeout_seconds, 15))
        client = OpenAI(
            api_key=self.settings.openai_api_key,
            timeout=timeout_seconds,
            max_retries=0,
        )
        response = client.chat.completions.create(
            model=self.settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        content = self._extract_content(response)
        prompt_tokens = getattr(response.usage, "prompt_tokens", None)
        completion_tokens = getattr(response.usage, "completion_tokens", None)
        cost = self._estimate_cost(prompt_tokens, completion_tokens)
        return LLMResponse(
            content=content,
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
            cost_usd=cost,
        )

    def _extract_content(self, response: Any) -> str:
        choices = getattr(response, "choices", None)
        if not choices:
            return "No content returned by model."
        message = choices[0].message
        content = getattr(message, "content", None)
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            text_parts = [
                block.get("text", "")
                for block in content
                if isinstance(block, dict) and isinstance(block.get("text"), str)
            ]
            if text_parts:
                return "\n".join(text_parts)
        return str(content)

    def _estimate_cost(self, input_tokens: int | None, output_tokens: int | None) -> float | None:
        if input_tokens is None or output_tokens is None:
            return None
        model_name = self.settings.openai_model.lower()
        # Approximate pricing for lab benchmarking only.
        if "gpt-4o-mini" in model_name:
            input_rate = 0.15 / 1_000_000
            output_rate = 0.60 / 1_000_000
        else:
            input_rate = 1.00 / 1_000_000
            output_rate = 3.00 / 1_000_000
        return round((input_tokens * input_rate) + (output_tokens * output_rate), 6)

    def _fallback_response(self, user_prompt: str, reason: str) -> LLMResponse:
        digest = sha256(user_prompt.encode("utf-8")).hexdigest()[:8]
        first_line = user_prompt.strip().splitlines()[0] if user_prompt.strip() else "Empty prompt"
        content = (
            "Fallback response generated locally.\n"
            f"Reason: {reason}\n"
            f"Prompt hash: {digest}\n"
            f"Summary: {first_line[:240]}"
        )
        return LLMResponse(content=content)
