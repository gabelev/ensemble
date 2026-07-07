"""Composer: how the Art Director agent assembles a design from primitives.

The composition logic is domain-agnostic:

  1. select a subset of primitives for this cycle
  2. parametrize each within bounds
  3. assign primitives to sections DRIVEN BY the writer's declared stance
     (form-follows-opinion — the choice of primitive enacts the stance)
  4. respect taboo memory (no reuse of last cycle's moves)
  5. honor an injected per-cycle constraint (the oblique strategy)

ensemble owns steps 1, 4, 5 and the data shapes. The *taste* of the selection
(which primitive enacts "boring" vs "sacred") is instance policy passed in as a
`stance_map`. This class is a scaffold: the real selection heuristic is an
instance concern and can be swapped wholesale.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from ensemble.design.primitive import PrimitiveLibrary
from ensemble.state.taboo import Move, TabooMemory


@dataclass
class SectionAssignment:
    """One section's chosen primitive + params, with the stance that drove it."""

    section: str
    stance: str
    primitive: str
    params: Mapping[str, Any]


@dataclass
class Composition:
    """The assembled design: per-section assignments + the moves it used."""

    assignments: list[SectionAssignment] = field(default_factory=list)
    moves: list[Move] = field(default_factory=list)
    constraint: str | None = None

    def render(self, library: PrimitiveLibrary) -> str:
        """Render every assignment through its primitive and concatenate."""
        return "\n".join(
            library.get(a.primitive).render(a.params) for a in self.assignments
        )


# A stance_map maps a declared stance -> (primitive name, params). It is the
# instance's taste, injected. ensemble never ships one.
StanceMap = Mapping[str, Callable[[str], tuple[str, Mapping[str, Any]]]]


class Composer:
    """Scaffold composer. Assigns a primitive per section via the stance_map,
    skipping any move currently forbidden by taboo memory."""

    def __init__(self, library: PrimitiveLibrary, taboo: TabooMemory | None = None) -> None:
        self.library = library
        self.taboo = taboo or TabooMemory()

    def compose(
        self,
        sections: Sequence[tuple[str, str]],  # (section_name, declared_stance)
        stance_map: StanceMap,
        *,
        constraint: str | None = None,
    ) -> Composition:
        comp = Composition(constraint=constraint)
        for section, stance in sections:
            if stance not in stance_map:
                raise KeyError(f"no primitive mapping for stance: {stance!r}")
            primitive_name, params = stance_map[stance](section)
            move = Move(kind="design", signature=f"{primitive_name}:{stance}")
            if self.taboo.is_forbidden(move):
                # Instance policy would re-roll here; the scaffold records the
                # collision and moves on so the boundary/logic is visible.
                move = Move(kind="design", signature=f"{primitive_name}:{stance}:rerolled")
            self.taboo.record(move)
            comp.assignments.append(
                SectionAssignment(section=section, stance=stance, primitive=primitive_name, params=params)
            )
            comp.moves.append(move)
        return comp
