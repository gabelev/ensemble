"""The stigmergic ledger: fragments accrete; the densest cluster is the theme.

The theme is never chosen top-down. Fragments (observations, tagged by beat)
pile up; a `Clusterer` finds the densest cluster; that cluster *is* the theme.
A planner names it — it does not invent it.

The ledger stores TEXTUAL fragments, so clustering here is generic. Any heavy
domain-specific perception (audio embeddings, vision) happens upstream in the
instance, before a fragment is written. That keeps this layer domain-agnostic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Protocol, Sequence, runtime_checkable


@dataclass(frozen=True)
class Fragment:
    """One observation dropped into the ledger.

    `beat` pre-tags the fragment by kind (an instance defines its beats, e.g.
    "verdict on one thing" vs "the field is moving this way"). Pre-tagging is
    most of what makes clustering legible.
    """

    id: str
    content: str
    beat: str
    author: str
    created_at: str  # ISO-8601; passed in by the instance (ensemble stays clock-free)
    tags: Sequence[str] = field(default_factory=tuple)
    embedding: Optional[Sequence[float]] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass
class Cluster:
    """A precipitated cluster of fragments and its density."""

    label: str
    fragments: list[Fragment]
    density: float

    @property
    def size(self) -> int:
        return len(self.fragments)


@runtime_checkable
class Ledger(Protocol):
    """Storage for fragments. Append and read over a window.

    Mold binds this to Chaos Dimension; tests bind an in-memory list.
    """

    def append(self, fragment: Fragment) -> None: ...

    def read(self, *, since: str | None = None, beat: str | None = None) -> Sequence[Fragment]: ...


@runtime_checkable
class Clusterer(Protocol):
    """Turns a bag of fragments into density-ranked clusters (the precipitation)."""

    def precipitate(self, fragments: Sequence[Fragment]) -> list[Cluster]: ...


class InMemoryLedger:
    """A list-backed Ledger for the slice and tests."""

    def __init__(self, seed: Sequence[Fragment] = ()) -> None:
        self._fragments: list[Fragment] = list(seed)

    def append(self, fragment: Fragment) -> None:
        self._fragments.append(fragment)

    def read(self, *, since: str | None = None, beat: str | None = None) -> Sequence[Fragment]:
        out = self._fragments
        if since is not None:
            out = [f for f in out if f.created_at >= since]
        if beat is not None:
            out = [f for f in out if f.beat == beat]
        return list(out)


# A default keyword clusterer. Deliberately simple: real instances inject an
# embedder-backed clusterer. This exists so the pipeline runs without one.
_STOPWORDS = frozenset(
    "the a an and or of to in on is it its as at by for with from this that these those "
    "not no we you they he she i be are was were been being into over under out "
    # contraction stems left behind by apostrophe splitting (didn't -> didn + t)
    "didn doesn isn wasn aren weren won don hasn haven hadn couldn shouldn wouldn "
    "can cant ll ve re dont its what when where which who whom how why "
    "did does do has have had will would could should there here their them his her "
    "your our my but so if then than just only also very "
    # near-empty nouns that ride along in almost any fragment
    "thing things something anything nothing way ways one ones".split()
)


_URLISH = frozenset("https http www com org net html php index sites".split())


def _keywords(text: str) -> list[str]:
    # URLs are provenance, not meaning — a field of sourced fragments must not
    # cluster on 'https'. Strip them before tokenizing.
    text = " ".join(w for w in text.split() if not w.startswith(("http://", "https://", "(http")))
    return [
        w
        for w in "".join(c.lower() if c.isalnum() else " " for c in text).split()
        if w not in _STOPWORDS and w not in _URLISH and len(w) > 2 and not w.isdigit()
    ]


class KeywordClusterer:
    """Groups fragments by shared keyword; density = fraction of the field a
    keyword touches.

    Clusters OVERLAP on purpose: a fragment counts toward every concept it
    contains, so "densest cluster" means "the concept the most fragments are
    reaching toward" — the stigmergic reading of a theme precipitating. This is
    a deliberately crude stand-in for embedding clustering and is meant to be
    swapped for a real `Clusterer` (inject one into `precipitate_theme`).
    """

    def precipitate(self, fragments: Sequence[Fragment]) -> list[Cluster]:
        if not fragments:
            return []
        total = len(fragments)
        by_keyword: dict[str, list[Fragment]] = {}
        occurrences: dict[str, int] = {}
        for f in fragments:
            kws = _keywords(f.content)
            for kw in set(kws):
                by_keyword.setdefault(kw, []).append(f)
            for kw in kws:
                occurrences[kw] = occurrences.get(kw, 0) + 1

        ranked = [
            Cluster(label=label, fragments=frags, density=len(frags) / total)
            for label, frags in by_keyword.items()
        ]
        # Densest first (fragments reached); then total occurrences (a word the
        # field keeps returning to beats a word mentioned once); alphabetical
        # last so the same field always precipitates the same theme.
        ranked.sort(key=lambda c: (-c.size, -occurrences[c.label], c.label))
        return ranked


def precipitate_theme(
    fragments: Sequence[Fragment],
    clusterer: Clusterer | None = None,
) -> Optional[Cluster]:
    """Return the densest cluster — the emergent theme — or None if the field is empty.

    This is the mechanical heart of stigmergy: the theme is whatever precipitated,
    not whatever was chosen.
    """
    clusterer = clusterer or KeywordClusterer()
    clusters = clusterer.precipitate(fragments)
    return clusters[0] if clusters else None
