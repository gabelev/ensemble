"""Versioned JSON state store for drifting persona/style state.

ensemble defines the store; the *shape* of the state and *where* it is persisted
are the instance's call. Mold persists these JSON/CSS blobs in its content repo
(terrarium) so drift is public and diff-able.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Protocol, runtime_checkable


@runtime_checkable
class StateStore(Protocol):
    """Load/save versioned JSON state by key (e.g. persona name)."""

    def load(self, key: str) -> dict[str, Any]: ...

    def save(self, key: str, state: Mapping[str, Any]) -> None: ...


class JsonFileStateStore:
    """Stores each state blob as `<root>/<key>.json`.

    Point `root` at a path inside the instance's content repo so every save is a
    diffable change. ensemble does not know or care that the repo is public.
    """

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self.root / f"{key}.json"

    def load(self, key: str) -> dict[str, Any]:
        p = self._path(key)
        if not p.exists():
            return {}
        return json.loads(p.read_text())

    def save(self, key: str, state: Mapping[str, Any]) -> None:
        self._path(key).write_text(json.dumps(dict(state), indent=2, sort_keys=True) + "\n")
