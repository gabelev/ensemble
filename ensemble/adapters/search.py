"""Search adapters implementing the perceive.SearchAdapter protocol.

`AnthropicWebSearch` is the batteries-included default: it drives the
Anthropic Messages API web_search server tool and structures what came back
into dated `Evidence`. Generic — instances define their own queries and
windows; nothing domain-specific lives here.

Extraction uses a LINE-DELIMITED record format, not JSON: model summaries
routinely contain unescaped quotes (song/film titles), which make emitted
JSON unparseable and silently drop every candidate. Labeled lines separated
by `---` can't be broken by quotes or brackets in the values.
"""

from __future__ import annotations

from datetime import date
from typing import Sequence

from ensemble.perceive import Evidence
from ensemble.providers.model import Message

_EXTRACT_PROMPT = """Search the web for: {query}

From the results, list every distinct, real, current artifact or story found.
For EACH one, output a record in EXACTLY this format:

TITLE: <the named work/artifact/event>
URL: <source URL>
DATE: <publication date as YYYY-MM-DD>
SUMMARY: <2-3 factual sentences: what it is, the concrete numbers/facts the source gives, why it matters now>
---

Separate every record with a line containing only three dashes. Put each field
on ONE line. Only include a record if you actually saw a real source URL and a
publication date — skip anything you cannot date. Facts only, no interpretation.
Do not wrap the output in code fences. Today is {today}."""


class AnthropicWebSearch:
    """SearchAdapter over the Anthropic web_search server tool."""

    name = "anthropic-web-search"

    def __init__(self, provider, *, max_searches: int = 5, max_results: int = 8) -> None:
        # provider: ensemble.providers.anthropic.AnthropicProvider
        self.provider = provider
        self.max_searches = max_searches
        self.max_results = max_results

    def search(self, query: str, *, now: date) -> Sequence[Evidence]:
        reply = self.provider.complete_with_web_search(
            [Message(role="user", content=_EXTRACT_PROMPT.format(query=query, today=now.isoformat()))],
            max_searches=self.max_searches,
        )
        return self._parse(reply, now)

    def _parse(self, reply: str, now: date) -> list[Evidence]:
        out: list[Evidence] = []
        for block in reply.split("---"):
            fields = self._fields(block)
            title, url = fields.get("title", ""), fields.get("url", "")
            published = fields.get("date", "")
            if not title or not url.startswith(("http://", "https://")) or not published:
                continue
            out.append(Evidence(
                title=title,
                url=url,
                published=published[:10],
                summary=fields.get("summary", ""),
                source=self.name,
                fetched_at=now.isoformat(),
            ))
            if len(out) >= self.max_results:
                break
        return out

    @staticmethod
    def _fields(block: str) -> dict[str, str]:
        """Pull labeled lines from one record. Later summary lines (rare wraps)
        fold into the summary; everything else is single-line."""
        fields: dict[str, str] = {}
        current: str | None = None
        for line in block.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            key = None
            for label in ("TITLE", "URL", "DATE", "SUMMARY"):
                if stripped.upper().startswith(label + ":"):
                    key = label.lower()
                    fields[key] = stripped[len(label) + 1:].strip()
                    current = key
                    break
            if key is None and current == "summary":
                fields["summary"] = (fields.get("summary", "") + " " + stripped).strip()
        return fields
