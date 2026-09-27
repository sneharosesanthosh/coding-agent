"""
Thin wrapper around the Anthropic API.

Why a wrapper instead of calling `anthropic.Anthropic()` directly all over the
codebase? Two reasons:

1. Every other module (cli.py, and later the orchestrator/tool loop) should
   depend on *this* interface, not on the Anthropic SDK's exact shape. If we
   ever want to add OpenAI or a local model as an alternative backend, we
   only change this one file.
2. It's a natural place to centralize model choice, default max_tokens,
   retry logic, and (later) tool-schema plumbing.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from anthropic import Anthropic


DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_MAX_TOKENS = 4096


@dataclass
class LLMResponse:
    """Normalized response shape, independent of the raw SDK object."""

    text: str
    stop_reason: str | None
    raw: object  # keep the original response around for debugging / later tool-use parsing


class LLMClient:
    """Provider-agnostic-by-design, Claude-by-default LLM client."""

    def __init__(self, model: str = DEFAULT_MODEL, max_tokens: int = DEFAULT_MAX_TOKENS) -> None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key, "
                "or export it in your shell."
            )
        self._client = Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens

    def send(
        self,
        messages: list[dict],
        system: str | None = None,
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        """
        Send a conversation (list of {"role": ..., "content": ...} dicts) and
        get back a single assistant turn.

        Pass `tools=TOOL_SCHEMAS` to let Claude call tools; check
        `response.stop_reason == "tool_use"` and read `response.raw.content`
        for the tool_use blocks — the agent loop in agent.py does this.
        """
        kwargs = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = tools

        response = self._client.messages.create(**kwargs)

        # A response can contain multiple content blocks; for plain text
        # turns there's normally just one, but we join defensively.
        text = "".join(block.text for block in response.content if block.type == "text")

        return LLMResponse(text=text, stop_reason=response.stop_reason, raw=response)