"""Design composition: a primitive library + an agent that composes from it."""

from ensemble.design.primitive import Primitive, PrimitiveLibrary
from ensemble.design.composer import Composer, Composition, SectionAssignment

__all__ = ["Primitive", "PrimitiveLibrary", "Composer", "Composition", "SectionAssignment"]
