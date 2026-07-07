"""Episodic memory: what an agent remembers across cycles.

`EpisodicMemory` is a protocol. ensemble ships an in-memory impl for tests and
the vertical slice; instances bind a real store (e.g. pgvector) as an adapter.
"""

from __future__ import annotations

from typing import Any, Mapping, Protocol, Sequence, runtime_checkable


@runtime_checkable
class EpisodicMemory(Protocol):
    """A store of episodes an agent can write to and recall from.

    `recall` is intentionally query-shaped (not just "get all") so a vector
    store can implement semantic recall without changing the interface.
    """

    def remember(self, episode: Mapping[str, Any]) -> None: ...

    def recall(self, query: Mapping[str, Any] | None = None, *, limit: int = 10) -> Sequence[Mapping[str, Any]]: ...


class InMemoryMemory:
    """A trivial list-backed EpisodicMemory. Not for production; good for tests."""

    def __init__(self) -> None:
        self._episodes: list[Mapping[str, Any]] = []

    def remember(self, episode: Mapping[str, Any]) -> None:
        self._episodes.append(dict(episode))

    def recall(self, query: Mapping[str, Any] | None = None, *, limit: int = 10) -> Sequence[Mapping[str, Any]]:
        # No semantic matching here — return most-recent. A real adapter ranks.
        return list(reversed(self._episodes))[:limit]
