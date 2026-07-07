"""ensemble — a domain-agnostic framework for creative multi-agent systems.

ensemble ships *mechanisms*; an instance (e.g. Mold) ships *content*. Nothing
instance-specific belongs in this package. See ARCHITECTURE.md.
"""

from ensemble.agent import Agent, Persona, SelfState, Perception, Decision, Artifact, PublishResult
from ensemble.ledger import Fragment, Ledger, Cluster, Clusterer, precipitate_theme
from ensemble.pipeline import Stage, Pipeline
from ensemble.providers.model import ModelProvider, Message, MockProvider

__version__ = "0.0.1"

__all__ = [
    "Agent",
    "Persona",
    "SelfState",
    "Perception",
    "Decision",
    "Artifact",
    "PublishResult",
    "Fragment",
    "Ledger",
    "Cluster",
    "Clusterer",
    "precipitate_theme",
    "Stage",
    "Pipeline",
    "ModelProvider",
    "Message",
    "MockProvider",
    "__version__",
]
