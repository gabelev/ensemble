"""PERCEIVE: the mandatory perception stage.

Perception, not generation, is the quality ceiling. This stage runs BEFORE any
author writes and the pipeline hard-fails pieces it cannot ground — an
optional tool is a skipped tool, so this one is a stage, not a tool.

Domain-agnostic mechanics (adapters/sinks are instance wiring):

- `Evidence` — one dated, sourced observation. No date or no URL means the
  recency filter discards it before anyone reasons about it.
- `SearchAdapter` — pluggable source (web search, an audio surveyor, an RSS
  pull). Receives the ACTUAL current date so queries never reach for a
  remembered year.
- `Perceiver.broad_scan` — Pass 1, cycle start: what is moving in the field;
  candidates feed the instance's stigmergic ledger.
- `Perceiver.deep_verify` — Pass 2, per committed piece: current facts about
  one subject, pulled immediately before writing.
- `ProvenanceSink` — every kept Evidence is logged (URL, dates, claim) so
  recency and sourcing are auditable after the fact.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Callable, Mapping, Protocol, Sequence, runtime_checkable


@dataclass(frozen=True)
class Evidence:
    """One dated, sourced observation of the outside world."""

    title: str                      # the named work/artifact/event
    url: str                        # source URL — required
    published: str                  # ISO date (YYYY-MM-DD) — required
    summary: str                    # what the source says (described, not reproduced)
    source: str = "unknown"         # adapter name
    fetched_at: str = ""            # ISO date the fetch happened
    metadata: Mapping[str, Any] = field(default_factory=dict)


@runtime_checkable
class SearchAdapter(Protocol):
    """A perception source. `now` is injected so queries carry the real date."""

    name: str

    def search(self, query: str, *, now: date) -> Sequence[Evidence]: ...


@runtime_checkable
class ProvenanceSink(Protocol):
    """Where kept evidence is logged for auditability."""

    def record(self, cycle_id: str, evidence: Evidence, claim: str | None = None) -> None: ...


def _parse_date(value: str) -> date | None:
    try:
        return datetime.fromisoformat(value.strip()[:10]).date()
    except (ValueError, AttributeError):
        return None


def recency_filter(
    candidates: Sequence[Evidence], *, now: date, window_days: int
) -> list[Evidence]:
    """The recency contract, enforced by data: no date or no URL -> discarded;
    outside the rolling window -> rejected. Never negotiable by a prompt."""
    kept = []
    floor = now - timedelta(days=window_days)
    for e in candidates:
        if not (e.url or "").startswith(("http://", "https://")):
            continue
        published = _parse_date(e.published or "")
        if published is None:
            continue
        if published < floor or published > now:
            continue
        kept.append(e)
    return kept


def format_query(template: str, now: date) -> str:
    """Inject the actual current date into a query template. Supported slots:
    {today} (ISO), {month_year} ("July 2026"), {year}. Templates without slots
    get " {month_year}" appended — a dateless query is how evergreen SEO
    sludge gets in."""
    slots = {
        "today": now.isoformat(),
        "month_year": now.strftime("%B %Y"),
        "year": str(now.year),
    }
    if any("{" + k + "}" in template for k in slots):
        return template.format(**slots)
    return f"{template} {slots['month_year']}"


class Perceiver:
    """Runs the two perception passes over pluggable adapters."""

    def __init__(
        self,
        adapters: Sequence[SearchAdapter],
        *,
        window_days: int = 30,
        sink: ProvenanceSink | None = None,
        clock: Callable[[], date] = date.today,
    ) -> None:
        if not adapters:
            raise ValueError("Perceiver needs at least one SearchAdapter")
        self.adapters = list(adapters)
        self.window_days = window_days
        self.sink = sink
        self.clock = clock

    def broad_scan(self, queries: Sequence[str], *, cycle_id: str = "") -> list[Evidence]:
        """Pass 1: survey the field. Dated candidates only; dedup by URL."""
        return self._run(queries, cycle_id=cycle_id, claim=None)

    def deep_verify(self, subject: str, *, cycle_id: str = "",
                    extra_queries: Sequence[str] = ()) -> list[Evidence]:
        """Pass 2: current facts about one committed subject, pulled right
        before writing. Stale figures are the tell of a machine that didn't
        actually look."""
        queries = [f"{subject} latest {{month_year}}", *extra_queries]
        return self._run(queries, cycle_id=cycle_id, claim=subject)

    def _run(self, queries: Sequence[str], *, cycle_id: str, claim: str | None) -> list[Evidence]:
        now = self.clock()
        seen: dict[str, Evidence] = {}
        for adapter in self.adapters:
            for template in queries:
                query = format_query(template, now)
                for e in adapter.search(query, now=now):
                    if e.url not in seen:
                        seen[e.url] = e
        kept = recency_filter(list(seen.values()), now=now, window_days=self.window_days)
        if self.sink is not None:
            for e in kept:
                self.sink.record(cycle_id, e, claim)
        return kept
