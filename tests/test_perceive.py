"""The recency contract is data, not prompt hope."""

from __future__ import annotations

from datetime import date

from ensemble.perceive import Evidence, Perceiver, format_query, recency_filter

NOW = date(2026, 7, 8)


def _e(**kw) -> Evidence:
    base = dict(title="t", url="https://x.example/a", published="2026-07-01",
                summary="s", source="test")
    base.update(kw)
    return Evidence(**base)


def test_recency_filter_discards_undated_and_unsourced() -> None:
    candidates = [
        _e(),                                   # in window
        _e(url="", published="2026-07-01"),     # no URL -> discarded
        _e(url="https://x.example/b", published=""),        # no date -> discarded
        _e(url="https://x.example/c", published="garbage"),  # unparseable -> discarded
        _e(url="https://x.example/d", published="2026-01-01"),  # stale -> rejected
        _e(url="https://x.example/e", published="2026-08-01"),  # future -> rejected
    ]
    kept = recency_filter(candidates, now=NOW, window_days=30)
    assert [e.url for e in kept] == ["https://x.example/a"]


def test_window_is_tunable() -> None:
    april = [_e(published="2026-04-17")]
    assert recency_filter(april, now=NOW, window_days=30) == []
    assert len(recency_filter(april, now=NOW, window_days=90)) == 1


def test_query_date_injection() -> None:
    assert format_query("AI music trends {month_year}", NOW) == "AI music trends July 2026"
    # A dateless template gets the date appended — never a bare evergreen query.
    assert format_query("AI music trends", NOW).endswith("July 2026")


class _StaticAdapter:
    name = "static"

    def __init__(self, evidence):
        self.evidence = evidence
        self.queries: list[str] = []

    def search(self, query, *, now):
        self.queries.append(query)
        return self.evidence


class _ListSink:
    def __init__(self):
        self.rows = []

    def record(self, cycle_id, evidence, claim=None):
        self.rows.append((cycle_id, evidence.url, claim))


def test_perceiver_dedups_filters_and_logs_provenance() -> None:
    adapter = _StaticAdapter([_e(), _e(), _e(url="https://x.example/old", published="2025-01-01")])
    sink = _ListSink()
    p = Perceiver([adapter], window_days=30, sink=sink, clock=lambda: NOW)

    kept = p.broad_scan(["what moved in AI music"], cycle_id="000")
    assert len(kept) == 1  # deduped by URL, stale one filtered
    assert sink.rows == [("000", "https://x.example/a", None)]
    assert adapter.queries and "July 2026" in adapter.queries[0]

    kept = p.deep_verify("IngaRose Celebrate Me", cycle_id="000")
    assert sink.rows[-1][2] == "IngaRose Celebrate Me"  # claim logged
    assert any("IngaRose" in q for q in adapter.queries[1:])
