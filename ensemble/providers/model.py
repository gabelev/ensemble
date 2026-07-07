"""ModelProvider: the one seam every model call goes through.

Agents never import a vendor SDK directly. They call a `ModelProvider`. That
makes the whole system testable on `MockProvider` and swappable between vendors
without touching agent code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol, Sequence, runtime_checkable


@dataclass(frozen=True)
class Message:
    """One chat turn."""

    role: str  # "system" | "user" | "assistant"
    content: str


@runtime_checkable
class ModelProvider(Protocol):
    """A chat + (optional) vision model behind a uniform call.

    `complete` takes messages and returns text. `describe_image` is the vision
    seam used by the design pass to critique rendered pixels; providers without
    vision may raise NotImplementedError.
    """

    def complete(self, messages: Sequence[Message], **kwargs: Any) -> str: ...

    def describe_image(self, image: bytes, prompt: str, **kwargs: Any) -> str: ...


class MockProvider:
    """A deterministic, offline ModelProvider for tests and the vertical slice.

    You seed it with a responder: `(messages) -> str`. Default echoes a stub so
    the pipeline runs with zero network and fully predictable output.
    """

    def __init__(self, responder: Callable[[Sequence[Message]], str] | None = None) -> None:
        self._responder = responder or self._default
        self.calls: list[Sequence[Message]] = []

    @staticmethod
    def _default(messages: Sequence[Message]) -> str:
        last = messages[-1].content if messages else ""
        return f"[mock completion for: {last[:80]}]"

    def complete(self, messages: Sequence[Message], **kwargs: Any) -> str:
        self.calls.append(list(messages))
        return self._responder(messages)

    def describe_image(self, image: bytes, prompt: str, **kwargs: Any) -> str:
        return f"[mock vision: {prompt[:80]}]"
