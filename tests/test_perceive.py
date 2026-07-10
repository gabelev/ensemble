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


def test_web_search_parser_survives_quotes_in_summaries() -> None:
    """The real-world failure: unescaped quotes in titles/summaries. The
    delimited format must not drop the record the way JSON did."""
    from ensemble.adapters.search import AnthropicWebSearch

    reply = (
        'Based on the search:\n\n'
        'TITLE: "Walk My Walk" by Breaking Rust\n'
        'URL: https://billboard.com/x\n'
        'DATE: 2026-07-02\n'
        'SUMMARY: The AI act\'s single "Walk My Walk" hit No. 1; fans call it "uncanny".\n'
        '---\n'
        'TITLE: IngaRose chart run\n'
        'URL: https://forbes.com/y\n'
        'DATE: 2026-06-28\n'
        'SUMMARY: #1 in five countries.\n'
        '---\n'
        'TITLE: undated rumor\n'
        'URL: https://example.com/z\n'
        'SUMMARY: no date so must be dropped.\n'
    )
    adapter = AnthropicWebSearch.__new__(AnthropicWebSearch)
    adapter.max_results = 8
    rows = adapter._parse(reply, NOW)
    assert [e.url for e in rows] == ["https://billboard.com/x", "https://forbes.com/y"]
    assert 'uncanny' in rows[0].summary  # quotes preserved, record intact


def test_deep_verify_uses_facts_path_no_window() -> None:
    """Deep-verify pulls current facts about an in-window subject WITHOUT
    re-applying the recency window (the bug that returned nothing)."""
    from ensemble.perceive import Evidence, Perceiver

    class _FactsAdapter:
        name = "facts"

        def search(self, query, *, now):
            return []  # broad path unused here

        def search_facts(self, subject, *, now):
            # an undated chart page + an old-but-canonical source; both kept
            return [
                Evidence(title=subject, url="https://chart.example/now",
                         published=now.isoformat(), summary="No.1, 3.6M streams", source="facts"),
                Evidence(title=subject, url="https://forbes.example/apr",
                         published="2026-04-01", summary="220k followers", source="facts"),
            ]

    sink = _ListSink()
    p = Perceiver([_FactsAdapter()], window_days=30, sink=sink, clock=lambda: NOW)
    kept = p.deep_verify("IngaRose", cycle_id="000")
    # Both survive — the April source would have been window-filtered by broad scan.
    assert {e.url for e in kept} == {"https://chart.example/now", "https://forbes.example/apr"}
    assert all(row[2] == "IngaRose" for row in sink.rows)


def test_facts_parser_keeps_undated_records() -> None:
    from ensemble.adapters.search import AnthropicWebSearch

    reply = (
        "FACT: IngaRose 'Celebrate Me' is No. 1 on iTunes in five countries\n"
        "URL: https://forbes.com/a\n"
        "DATE:\n"        # no date — must still be kept
        "---\n"
        "FACT: 220,000 followers\nURL: https://tiktok.com/b\nDATE: 2026-07-05\n"
        "---\n"
        "FACT: missing url\nURL: not-a-url\nDATE: 2026-07-01\n"
    )
    a = AnthropicWebSearch.__new__(AnthropicWebSearch)
    a.max_results = 8
    rows = a._parse_facts_test = None
    # exercise via the block loop used by search_facts
    from datetime import date as _date
    out = []
    for block in reply.split("---"):
        f = a._fields(block)
        if f.get("fact") and f.get("url", "").startswith("http"):
            out.append(f["url"])
    assert out == ["https://forbes.com/a", "https://tiktok.com/b"]
