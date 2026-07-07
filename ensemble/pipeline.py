"""Deterministic pipeline orchestration.

The authoring pipeline is a fixed DAG, NOT work-stealing:

    planning -> authors (parallel fan-out) -> editor -> design -> verify -> publish

`Stage` wraps a callable `(context) -> result`; `Pipeline` runs stages in order,
threading each stage's output into a shared, growing context. `fan_out` runs a
set of stages in parallel and collects their results.

This is an ensemble-native runner: no heavy orchestration dependency in the
core. A LangGraph backend can be added later as an optional adapter if control
flow outgrows a linear DAG — the `Stage`/`Pipeline` contract stays the same.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, MutableMapping, Sequence

StageFn = Callable[[MutableMapping[str, Any]], Any]


@dataclass
class Stage:
    """A named step. `run(context)` returns a value stored under `key` (default `name`)."""

    name: str
    fn: StageFn
    key: str | None = None

    def run(self, context: MutableMapping[str, Any]) -> Any:
        return self.fn(context)

    @property
    def out_key(self) -> str:
        return self.key or self.name


@dataclass
class Pipeline:
    """Runs stages in declared order, accumulating results into one context.

    Each stage sees everything prior stages produced. This is deliberate: the
    editor reads the authors' output, design reads the edited copy, etc.
    """

    stages: list[Stage] = field(default_factory=list)

    def then(self, name: str, fn: StageFn, *, key: str | None = None) -> "Pipeline":
        self.stages.append(Stage(name=name, fn=fn, key=key))
        return self

    def run(self, context: MutableMapping[str, Any] | None = None) -> MutableMapping[str, Any]:
        ctx: MutableMapping[str, Any] = dict(context or {})
        for stage in self.stages:
            ctx[stage.out_key] = stage.run(ctx)
        return ctx


def fan_out(
    stages: Sequence[Stage],
    context: Mapping[str, Any],
    *,
    max_workers: int | None = None,
) -> dict[str, Any]:
    """Run stages in parallel (the authors step). Returns {out_key: result}.

    Each parallel stage gets its own shallow copy of the context so concurrent
    writes don't collide; results are collected by the caller. Order of the
    returned mapping follows `stages`.
    """
    results: dict[str, Any] = {}
    if not stages:
        return results
    with ThreadPoolExecutor(max_workers=max_workers or len(stages)) as pool:
        futures = {pool.submit(s.run, dict(context)): s for s in stages}
        # Preserve declared order in the output mapping.
        done = {futures[f].out_key: f.result() for f in futures}
    for s in stages:
        results[s.out_key] = done[s.out_key]
    return results
