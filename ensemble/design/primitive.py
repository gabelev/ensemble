"""Primitives: parametrized, testable design components.

ensemble knows a primitive has a name, a parameter schema, and renders to a
string given params. It does NOT know the medium. For Mold a primitive renders
CSS/SVG; for another instance it might render something else entirely. The
human-authored kit lives in the instance, never here.
"""

from __future__ import annotations

from typing import Any, Mapping, Protocol, runtime_checkable


@runtime_checkable
class Primitive(Protocol):
    """A named, parametrized component that renders to a string fragment."""

    name: str

    @property
    def params_schema(self) -> Mapping[str, Any]:
        """Describe accepted params + their bounds (instance-defined shape)."""
        ...

    def render(self, params: Mapping[str, Any]) -> str:
        """Render this primitive with `params` to a fragment (e.g. CSS/SVG)."""
        ...


class PrimitiveLibrary:
    """A registry of primitives an agent can select and parametrize from."""

    def __init__(self) -> None:
        self._by_name: dict[str, Primitive] = {}

    def register(self, primitive: Primitive) -> None:
        if primitive.name in self._by_name:
            raise ValueError(f"primitive already registered: {primitive.name}")
        self._by_name[primitive.name] = primitive

    def get(self, name: str) -> Primitive:
        return self._by_name[name]

    def names(self) -> list[str]:
        return list(self._by_name)

    def __len__(self) -> int:
        return len(self._by_name)
