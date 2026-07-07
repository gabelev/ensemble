"""Judge: one grounded critic in the discriminator panel.

The load-bearing idea: disagreement between same-lineage models is fake, so each
judge must anchor to a DIFFERENT external reference. ensemble defines the Judge
contract and the score shape; the instance supplies the grounding (a corpus, a
lineage, a negative reference) and the actual scoring model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, runtime_checkable


@dataclass(frozen=True)
class ScoreVector:
    """Scores across over-determined anchors. NEVER collapsed to one scalar.

    Keys are anchor names (instance-defined, e.g. distance-from-negative-corpus,
    kinship-not-identity, taboo-compliance, stance-enactment, risk-floor). Each
    value is in [0, 1]. The discriminator requires passing all, not a weighted
    sum — a single scalar is exactly what a generator learns to game.
    """

    anchors: Mapping[str, float]

    def passes(self, thresholds: Mapping[str, float]) -> bool:
        return all(self.anchors.get(k, 0.0) >= t for k, t in thresholds.items())


@dataclass(frozen=True)
class Verdict:
    """A judge's decision on one candidate."""

    passed: bool
    scores: ScoreVector
    rationale: str = ""
    grounding: str = ""  # which reference this judge anchored to


@runtime_checkable
class Judge(Protocol):
    """Scores a candidate against this judge's own grounding reference."""

    grounding: str

    def evaluate(self, candidate: Mapping[str, Any]) -> Verdict: ...
