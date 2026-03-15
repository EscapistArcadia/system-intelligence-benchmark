"""Artifact build oracle for EMT (OSDI'25).

Validates:
  - Repository working directory exists.
  - Build commands execute successfully (captures stdout/stderr/return code).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
import logging
from pathlib import Path
import multiprocessing

from evaluator.oracle_artifact_build_primitives import (
    BuildCommandRequirement,
    OracleArtifactBuildBase,
)
from evaluator.utils import EntryConfig, BaseRequirement


@dataclass(frozen=True, slots=True, kw_only=True)
class BuildTarget:
    """Declarative description of one build command to run.

    Kept intentionally thin: the base primitive (BuildCommandRequirement) performs
    the authoritative validation and normalization.
    """

    name: str
    cmd: Sequence[str]
    relative_workdir: Path | None = None
    optional: bool = False
    timeout_seconds: float = 60.0
    env_overrides: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("BuildTarget.name must be non-empty")

        object.__setattr__(self, "cmd", tuple(self.cmd))

        if self.relative_workdir is not None and not isinstance(
            self.relative_workdir, Path
        ):
            object.__setattr__(self, "relative_workdir", Path(self.relative_workdir))


class OracleArtifactBuild(OracleArtifactBuildBase):
    """The artifact build oracle for artifact-core.

    Defaults:
      * Runs build commands in the repo keyed by config.name.
      * EntryConfig.repository_paths is expected to contain an entry for config.name.
    """

    _DEFAULT_TARGET_SPECS: tuple[tuple[str, tuple[str, ...], float], ...] = (
        (
            "qemu-system-x86_64: radix paging",
            ("make", "-j", str(multiprocessing.cpu_count()), "-C", "qemu-radix"),
            60.0,
            None,
        ),
        (
            "EMT-Linux: radix paging",
            ("make", "-j", str(multiprocessing.cpu_count()), "-C", "emt-linux-radix", "LOCALVERSION=-gen-x86"),
            120.0,
            None,
        ),
        (
            "qemu-system-x86_64: ecpt paging",
            ("make", "-j", str(multiprocessing.cpu_count()), "-C", "qemu-ecpt"),
            60.0,
            None,
        ),
        (
            "EMT-Linux: ecpt paging",
            ("make", "-j", str(multiprocessing.cpu_count()), "-C", "emt-linux-ecpt", "LOCALVERSION=-gen-x86"),
            120.0,
            None,
        ),
        (
            "docker image: dynamoRIO & performance analysis",
            ("docker", "build", "-t", "dynamorio:latest", "."),
            240.0,
            "dynamorio",
        ),
    )

    def __init__(
        self,
        *,
        config: EntryConfig,
        logger: logging.Logger,
        targets: Sequence[BuildTarget] | None = None,
    ) -> None:
        super().__init__(logger=logger)
        self._config = config

        if targets is None:
            targets = self._make_default_targets()
        self._targets = tuple(targets)

        names = [t.name for t in self._targets]
        if len(names) != len(set(names)):
            raise ValueError(f"Duplicate build target names: {names!r}")

    def _make_default_targets(self) -> tuple[BuildTarget, ...]:
        return tuple(
            BuildTarget(name=name, cmd=cmd, timeout_seconds=timeout_seconds, relative_workdir=workdir)
            for (name, cmd, timeout_seconds, workdir) in self._DEFAULT_TARGET_SPECS
        )

    def requirements(self) -> Sequence[BaseRequirement]:
        """Returns an ordered list of build requirements to validate."""
        repo_root = self._config.repository_paths.get(self._config.name)

        if repo_root is None:
            return (
                BuildCommandRequirement(
                    name=f"config: missing repository_paths entry for {self._config.name!r}",
                    optional=False,
                    cwd=Path(self._config.home_dir) / "__MISSING_REPOSITORY_PATH__",
                    cmd=("true",),
                    timeout_seconds=1.0,
                ),
            )

        return tuple(
            BuildCommandRequirement(
                name=target.name,
                optional=target.optional,
                cwd=repo_root,
                cmd=target.cmd,
                relative_workdir=target.relative_workdir,
                timeout_seconds=target.timeout_seconds,
                env_overrides=target.env_overrides,
            )
            for target in self._targets
        )
