"""Anthropic Claude adapter for the ModelProvider protocol.

Deliberately stdlib-only (urllib) so ensemble keeps zero runtime dependencies.
Chat via the Messages API; vision via base64 image content blocks. Retries with
exponential backoff on 429/5xx/overloaded.
"""

from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.request
from typing import Any, Sequence

from ensemble.providers.model import Message

_API_URL = "https://api.anthropic.com/v1/messages"
_API_VERSION = "2023-06-01"
_RETRYABLE = {429, 500, 502, 503, 529}


class AnthropicProvider:
    """ModelProvider backed by the Anthropic Messages API."""

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "claude-sonnet-5",
        vision_model: str | None = None,
        max_tokens: int = 4096,
        max_retries: int = 4,
        timeout: float = 120.0,
    ) -> None:
        if not api_key:
            raise ValueError("AnthropicProvider requires an api_key")
        self.api_key = api_key
        self.model = model
        self.vision_model = vision_model or model
        self.max_tokens = max_tokens
        self.max_retries = max_retries
        self.timeout = timeout

    # -- ModelProvider ---------------------------------------------------------

    def complete(self, messages: Sequence[Message], **kwargs: Any) -> str:
        system, turns = self._split(messages)
        payload: dict[str, Any] = {
            "model": kwargs.get("model", self.model),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "messages": turns,
        }
        if system:
            payload["system"] = system
        if "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]
        data = self._post(payload)
        return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")

    def describe_image(self, image: bytes, prompt: str, **kwargs: Any) -> str:
        media_type = kwargs.get("media_type", "image/png")
        payload = {
            "model": kwargs.get("model", self.vision_model),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64.b64encode(image).decode(),
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        }
        data = self._post(payload)
        return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")

    # -- internals ---------------------------------------------------------------

    @staticmethod
    def _split(messages: Sequence[Message]) -> tuple[str, list[dict[str, str]]]:
        """The Messages API takes system as a top-level param, not a turn."""
        system_parts = [m.content for m in messages if m.role == "system"]
        turns = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]
        if not turns:  # API requires at least one user turn
            turns = [{"role": "user", "content": ""}]
        return "\n\n".join(system_parts), turns

    def complete_with_web_search(
        self, messages: Sequence[Message], *, max_searches: int = 5, **kwargs: Any
    ) -> str:
        """Chat completion with the Anthropic web_search server tool enabled.
        The API executes the searches; the reply text carries the findings."""
        system, turns = self._split(messages)
        payload: dict[str, Any] = {
            "model": kwargs.get("model", self.model),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "messages": turns,
            "tools": [{
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": max_searches,
            }],
        }
        if system:
            payload["system"] = system
        data = self._post(payload)
        return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode()
        last_err: Exception | None = None
        for attempt in range(self.max_retries + 1):
            req = urllib.request.Request(
                _API_URL,
                data=body,
                method="POST",
                headers={
                    "content-type": "application/json",
                    "x-api-key": self.api_key,
                    "anthropic-version": _API_VERSION,
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return json.loads(resp.read())
            except urllib.error.HTTPError as e:
                last_err = e
                if e.code not in _RETRYABLE:
                    detail = e.read().decode(errors="replace")[:500]
                    raise RuntimeError(f"Anthropic API error {e.code}: {detail}") from e
            except urllib.error.URLError as e:
                last_err = e
            if attempt < self.max_retries:
                time.sleep(min(2**attempt, 30))
        raise RuntimeError(f"Anthropic API unreachable after {self.max_retries + 1} attempts") from last_err
