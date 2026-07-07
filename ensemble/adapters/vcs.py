"""Version-control persistence with QA/PROD branches.

The publish stage writes artifacts to files and commits them. ensemble ships a
local-git implementation (no network) that the vertical slice uses; a GitHub
adapter is the same protocol with push + branch semantics on top.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Protocol, runtime_checkable


@dataclass(frozen=True)
class CommitResult:
    ok: bool
    sha: str = ""
    branch: str = ""
    detail: str = ""


@runtime_checkable
class VCS(Protocol):
    """Write files and commit them, optionally on a named branch."""

    def write_and_commit(
        self,
        files: Mapping[str, str],
        message: str,
        *,
        branch: str | None = None,
    ) -> CommitResult: ...


class LocalGitVCS:
    """Commits into a local git repo. No remote, no push. For the slice + tests.

    `root` must be an existing git working tree. Paths in `files` are relative
    to `root`. Author identity is set per-commit so the slice never depends on
    the machine's global git config.
    """

    def __init__(self, root: str | Path, *, author: str = "ensemble <bot@ensemble.local>") -> None:
        self.root = Path(root)
        self.author = author

    def _git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(self.root), *args],
            capture_output=True,
            text=True,
        )

    def write_and_commit(
        self,
        files: Mapping[str, str],
        message: str,
        *,
        branch: str | None = None,
    ) -> CommitResult:
        if not (self.root / ".git").exists():
            return CommitResult(ok=False, detail=f"not a git repo: {self.root}")

        if branch:
            # Switch to (or create) the target branch.
            res = self._git("checkout", "-B", branch)
            if res.returncode != 0:
                return CommitResult(ok=False, branch=branch, detail=res.stderr.strip())

        for rel, content in files.items():
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            add = self._git("add", rel)
            if add.returncode != 0:
                return CommitResult(ok=False, detail=add.stderr.strip())

        commit = self._git(
            "-c", f"user.name={self.author.split(' <')[0]}",
            "-c", f"user.email={self.author.split('<')[-1].rstrip('>')}",
            "commit", "-m", message,
        )
        if commit.returncode != 0:
            return CommitResult(ok=False, detail=commit.stdout.strip() + commit.stderr.strip())

        sha = self._git("rev-parse", "HEAD").stdout.strip()
        cur_branch = self._git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        return CommitResult(ok=True, sha=sha, branch=cur_branch)
