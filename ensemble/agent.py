"""The Agent abstraction: a persona running PERCEIVE -> DECIDE -> EXECUTE -> PUBLISH.

`Agent` is domain-agnostic. Instances subclass it per role (planner, author,
editor, ...) and supply the persona's voice via `Persona`. The loop, the
contracts, and the wiring live here; the content does not.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from ensemble.memory import EpisodicMemory, InMemoryMemory
from ensemble.providers.model import ModelProvider


@dataclass(frozen=True)
class Persona:
    """The *static* identity of an agent: who it is, independent of any cycle.

    Base prompt + personality live here. This is instance-authored content that
    is passed *into* ensemble; ensemble never hardcodes a persona.
    """

    name: str
    base_prompt: str
    personality: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass
class SelfState:
    """The *drifting* self-state of an agent, versioned issue-to-issue.

    Issue N is downstream of issue N-1's residue. Persisted by the instance in
    its content repo so drift is diff-able. ensemble only defines the shape.
    """

    version: int = 0
    obsessions: list[str] = field(default_factory=list)
    residue: Mapping[str, Any] = field(default_factory=dict)

    def bumped(self, **changes: Any) -> "SelfState":
        """Return a new SelfState with an incremented version (drift is explicit)."""
        return SelfState(
            version=self.version + 1,
            obsessions=list(changes.get("obsessions", self.obsessions)),
            residue=dict(changes.get("residue", self.residue)),
        )


# --- Loop payloads -----------------------------------------------------------
# Deliberately thin, generic containers. Instances put whatever they need in
# `.data`; ensemble does not interpret it.

@dataclass
class Perception:
    """What the agent took in during PERCEIVE."""

    data: Mapping[str, Any] = field(default_factory=dict)


@dataclass
class Decision:
    """What the agent resolved to do during DECIDE."""

    data: Mapping[str, Any] = field(default_factory=dict)


@dataclass
class Artifact:
    """What EXECUTE produced. `body` is the primary payload (e.g. Markdown)."""

    kind: str
    body: str
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass
class PublishResult:
    """Outcome of PUBLISH (e.g. commit sha, path, ledger ids)."""

    ok: bool
    refs: Mapping[str, Any] = field(default_factory=dict)


class Agent(ABC):
    """Base class for a creative agent running the PDE loop.

    Subclasses implement `perceive`, `decide`, `execute`, and (optionally)
    `publish`. `run` sequences them. Everything a subclass needs — model,
    memory, persona, drifting state — is injected, never global.
    """

    def __init__(
        self,
        persona: Persona,
        model: ModelProvider,
        *,
        self_state: Optional[SelfState] = None,
        memory: Optional[EpisodicMemory] = None,
    ) -> None:
        self.persona = persona
        self.model = model
        self.self_state = self_state or SelfState()
        self.memory = memory or InMemoryMemory()

    # -- PERCEIVE -> DECIDE -> EXECUTE -> PUBLISH -----------------------------

    @abstractmethod
    def perceive(self, context: Mapping[str, Any]) -> Perception:
        """Take in the world (ledger, prior artifacts, brief) -> Perception."""

    @abstractmethod
    def decide(self, perception: Perception) -> Decision:
        """Form an intention from a Perception."""

    @abstractmethod
    def execute(self, decision: Decision) -> Artifact:
        """Produce the artifact (usually the model call happens here)."""

    def publish(self, artifact: Artifact, context: Mapping[str, Any]) -> PublishResult:
        """Emit the artifact to sinks. Default is a no-op the pipeline handles.

        Many roles delegate persistence to the pipeline's publish stage; agents
        that publish directly (e.g. a surveyor dropping ledger fragments)
        override this.
        """
        return PublishResult(ok=True, refs={"artifact_kind": artifact.kind})

    def run(self, context: Mapping[str, Any]) -> Artifact:
        """Run PERCEIVE -> DECIDE -> EXECUTE and return the artifact.

        PUBLISH is separated so a pipeline can decide when/where to persist.
        """
        perception = self.perceive(context)
        decision = self.decide(perception)
        artifact = self.execute(decision)
        self.memory.remember({"persona": self.persona.name, "artifact_kind": artifact.kind})
        return artifact
