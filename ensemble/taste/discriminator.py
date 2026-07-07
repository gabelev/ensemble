"""Discriminator: the bar-keeper. Its only job is contempt.

Runs N heterogeneously-grounded judges and requires a candidate to survive ALL
of them. It is the inverse of a normal QA gate: a normal gate removes mistakes,
this gate removes the *absence* of mistakes — it forces regeneration toward
riskier, not more polished, output.

ensemble owns the harness (multi-judge, pass-all, warm-start hook). The judges,
their groundings, the corpora, the risk-floor, and the thresholds are all
instance-supplied. No aesthetic is hardcoded here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from ensemble.taste.judge import Judge, Verdict


@dataclass
class DiscriminationResult:
    """Outcome for one candidate: did it survive every judge, and why/why not."""

    accepted: bool
    verdicts: list[Verdict] = field(default_factory=list)

    @property
    def dissenters(self) -> list[Verdict]:
        return [v for v in self.verdicts if not v.passed]


class Discriminator:
    """A panel of independently-grounded judges. Pass-all or regenerate.

    `warm_start` is an optional human-pick hook: during bootstrap the system
    emits several candidates and a human picks one; each pick is preference data.
    When `warm_start` is None the panel runs fully autonomously.
    """

    def __init__(
        self,
        judges: Sequence[Judge],
        *,
        warm_start: Callable[[Sequence[Mapping[str, Any]]], int] | None = None,
    ) -> None:
        if not judges:
            raise ValueError("a discriminator needs at least one grounded judge")
        self.judges = list(judges)
        self.warm_start = warm_start

    def evaluate(self, candidate: Mapping[str, Any]) -> DiscriminationResult:
        """A candidate is accepted only if EVERY judge passes it."""
        verdicts = [j.evaluate(candidate) for j in self.judges]
        return DiscriminationResult(
            accepted=all(v.passed for v in verdicts),
            verdicts=verdicts,
        )

    def choose(self, candidates: Sequence[Mapping[str, Any]]) -> int:
        """Pick a winning candidate index.

        With a warm-start hook, defer to the human pick (and let the caller log
        it as preference data). Without one, choose the first candidate that
        survives the full panel; if none do, the whole batch is too safe —
        signal that by returning -1 so the caller regenerates riskier.
        """
        if self.warm_start is not None:
            return self.warm_start(candidates)
        for i, cand in enumerate(candidates):
            if self.evaluate(cand).accepted:
                return i
        return -1  # everything was too well-behaved: regenerate, don't polish
