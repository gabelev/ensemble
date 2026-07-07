"""Integration adapters behind protocols.

ensemble ships only the truly-generic adapters (local git, deploy protocol).
Instance-specific adapters (e.g. Mold's Chaos-Dimension ledger) start in the
instance and graduate here only when a second instance needs them.
"""

from ensemble.adapters.vcs import VCS, LocalGitVCS, CommitResult
from ensemble.adapters.deploy import Deploy, DeployResult

__all__ = ["VCS", "LocalGitVCS", "CommitResult", "Deploy", "DeployResult"]
