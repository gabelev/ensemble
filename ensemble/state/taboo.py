"""Taboo memory: the anti-repetition store that keeps output moving.

Every cycle logs the specific *moves* it used. Next cycle those moves are
forbidden (or penalized). This is the moving target that makes a discriminator
un-gameable and manufactures "never the same spread twice." ensemble defines
what a move-record looks like and the forbid/allow logic; the instance defines
what a move actually *is* (a design primitive+params+section, an opening
structure, a rhetorical tic).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class Move:
    """One recorded move. `signature` is the identity used for taboo matching.

    Instances choose the signature granularity: too coarse and everything gets
    forbidden; too fine and nothing does.
    """

    kind: str
    signature: str
    metadata: Mapping[str, Any] = field(default_factory=dict)


class TabooMemory:
    """Records moves per cycle and answers 'is this forbidden?'.

    A simple, exact-signature implementation. A richer instance may override
    `is_forbidden` with fuzzy/embedding-distance matching; the interface holds.
    """

    def __init__(self, forbidden: Iterable[Move] = ()) -> None:
        self._forbidden: set[str] = {m.signature for m in forbidden}
        self._this_cycle: list[Move] = []

    def is_forbidden(self, move: Move) -> bool:
        return move.signature in self._forbidden

    def record(self, move: Move) -> None:
        """Log a move used this cycle (becomes forbidden next cycle)."""
        self._this_cycle.append(move)

    def roll_over(self) -> "TabooMemory":
        """End the cycle: this cycle's moves become next cycle's forbidden set.

        Returns a fresh TabooMemory. The instance persists the forbidden set as
        versioned JSON alongside persona/style state.
        """
        return TabooMemory(forbidden=list(self._this_cycle))

    @property
    def forbidden_signatures(self) -> frozenset[str]:
        return frozenset(self._forbidden)

    @property
    def used_this_cycle(self) -> list[Move]:
        return list(self._this_cycle)
