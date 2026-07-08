"""Search adapters implementing the perceive.SearchAdapter protocol.

`AnthropicWebSearch` is the batteries-included default: it drives the
Anthropic Messages API web_search server tool and structures what came back
into dated `Evidence`. Generic — instances define their own queries and
windows; nothing domain-specific lives here.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Sequence

from ensemble.perceive import Evidence
from ensemble.providers.model import Message

_EXTRACT_PROMPT = """Search the web for: {query}

From the results, list every distinct, real, current artifact or story found.
Return ONLY a JSON array (no fences, no commentary), each element exactly:
{{"title": "<the named work/artifact/event>",
  "url": "<source URL>",
  "published": "<publication date, YYYY-MM-DD — omit the entry entirely if you cannot determine it>",
  "summary": "<2-3 factual sentences: what it is, the concrete numbers/facts the source gives, why it matters now>"}}

Rules: only include entries with a real source URL and a publication date you
actually saw. Facts only — no interpretation. Today is {today}."""


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
        text = reply.strip()
        start, end = text.find("["), text.rfind("]")
        if start < 0 or end <= start:
            return []
        try:
            rows = json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return []
        out = []
        for r in rows[: self.max_results]:
            if not isinstance(r, dict):
                continue
            out.append(Evidence(
                title=str(r.get("title", "")).strip(),
                url=str(r.get("url", "")).strip(),
                published=str(r.get("published", "")).strip(),
                summary=str(r.get("summary", "")).strip(),
                source=self.name,
                fetched_at=now.isoformat(),
            ))
        return out
