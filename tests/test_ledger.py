"""Framework-level test: a theme precipitates from the densest cluster."""

from __future__ import annotations

from ensemble.ledger import Fragment, InMemoryLedger, precipitate_theme


def _frag(i: int, content: str, beat: str = "b") -> Fragment:
    return Fragment(id=f"f{i}", content=content, beat=beat, author="a", created_at="2026-01-01T00:00:00Z")


def test_densest_cluster_becomes_theme() -> None:
    ledger = InMemoryLedger(seed=[
        _frag(0, "mold spreads across the substrate, colonizing culture"),
        _frag(1, "culture is growth on a substrate; colonizing everything"),
        _frag(2, "another note about culture and growth, colonizing"),
        _frag(3, "a lone unrelated fragment about weather"),
    ])
    theme = precipitate_theme(list(ledger.read()))
    assert theme is not None
    # The three culture/growth fragments outweigh the lone outlier.
    assert theme.size >= 3
    assert theme.label in {"culture", "growth", "colonizing", "substrate"}


def test_empty_field_precipitates_nothing() -> None:
    assert precipitate_theme([]) is None
