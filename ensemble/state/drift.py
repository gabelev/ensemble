"""DriftEngine: state N is computed from state N-1 plus the last cycle's residue.

Drift is what makes issue N downstream of issue N-1. ensemble defines the
contract; an instance supplies the actual drift rule (how obsessions shift, how
a palette temperature moves within gamut). Kept a protocol on purpose — the
interesting part is instance-specific and we refuse to hardcode a default rule
that would smuggle in an aesthetic.
"""

from __future__ import annotations

from typing import Any, Mapping, Protocol, runtime_checkable

from ensemble.agent import SelfState


@runtime_checkable
class DriftEngine(Protocol):
    """Advance drifting state by one cycle.

    `residue` is whatever the just-finished cycle left behind (themes hit,
    moves used, intensity). The engine folds it into the next state and bumps
    the version so the change is explicit and diffable.
    """

    def advance(self, current: SelfState, residue: Mapping[str, Any]) -> SelfState: ...
