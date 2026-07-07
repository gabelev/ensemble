"""Deploy adapter protocol.

A deploy takes a committed ref and publishes it (QA -> preview, PROD ->
production). ensemble only defines the seam; the concrete adapter (e.g. Vercel)
lives with whichever layer owns the hosting relationship.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class DeployResult:
    ok: bool
    url: str = ""
    environment: str = ""
    detail: str = ""


@runtime_checkable
class Deploy(Protocol):
    """Publish a committed ref to an environment ('preview' | 'production')."""

    def deploy(self, ref: str, *, environment: str) -> DeployResult: ...
