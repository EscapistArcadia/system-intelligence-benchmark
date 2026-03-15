"""Environment setup oracle for EMT (OSDI'25).

Validates:
  - Required tools and minimum versions where applicable.
  - Repository directory exists.
  - Ground-truth reference files exist.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Mapping, Sequence

from evaluator import utils
from evaluator.utils import EntryConfig
from evaluator.oracle_env_setup_primitives import (
  DependencyVersionRequirement,
  FilesystemPathRequirement,
  OracleEnvSetupBase,
  PathType,
  VersionCompare,
)


def _required_path(paths: Mapping[str, Path], key: str, *, label: str) -> Path:
  """Returns a required path from a mapping with a clear error."""
  try:
    return paths[key]
  except KeyError as e:
    raise ValueError(f"Missing {label}[{key!r}] in EntryConfig") from e


class OracleEnvSetup(OracleEnvSetupBase):
  """Validates environment prerequisites for EMT."""

  def __init__(self, *, config: EntryConfig, logger: logging.Logger) -> None:
    super().__init__(logger)
    self._config = config

  def requirements(self) -> Sequence[utils.BaseRequirement]:
    repo_root = _required_path(
      self._config.repository_paths, self._config.name, label="repository_paths"
    )

    # TODO: Update the required versions and tools based on actual EMT requirements.
    # [DONE] TODO: Update the dependency for generating the data.
    #              We only need pandas to read the generated csv files.
    # [DONE] TODO: The original version of the script also plotted the data, but we don't need them, we just need the data themselves.
    #              I have removed the plotting code at the very beginning.
    # TODO: Add git clone, git submodule update, and git switch command for debug purpose.
    reqs: list[utils.BaseRequirement] = [
      DependencyVersionRequirement(
        name = "docker",
        cmd = ("docker", "--version"),
        required_version = (28, 2, 2),
        compare = VersionCompare.GEQ,
      ),
      DependencyVersionRequirement(
        name = "ninja",
        cmd = ("ninja", "--version"),
        required_version = (1, 11, 0),
        compare = VersionCompare.GEQ,
      ),
      DependencyVersionRequirement(
        name = "pkg-config",
        cmd = ("pkg-config", "--version"),
        required_version = (1, 8, 1),
        compare = VersionCompare.GEQ,
      ),
      DependencyVersionRequirement(
        name = "libglib2.0-dev",
        cmd = ("pkg-config", "--modversion", "glib-2.0"),
        required_version = (0, 0, 0),
        compare = VersionCompare.GEQ,
      ),
      DependencyVersionRequirement(
        name = "libpixman-1-dev",
        cmd = ("pkg-config", "--modversion", "pixman-1"),
        required_version = (0, 42, 2),
        compare = VersionCompare.GEQ,
      ),
      DependencyVersionRequirement(
        name = "meson",
        cmd = ("meson", "--version"),
        required_version = (1, 3, 2),
        compare = VersionCompare.GEQ
      ),
      DependencyVersionRequirement(
        name = "bison",
        cmd = ("bison", "--version"),
        required_version = (3, 8, 2),
        compare = VersionCompare.GEQ
      ),
      DependencyVersionRequirement(
        name = "flex",
        cmd = ("flex", "--version"),
        required_version = (2, 6, 4),
        compare = VersionCompare.GEQ
      ),
      DependencyVersionRequirement(
        name = "libelf-dev",
        cmd = ("pkg-config", "--modversion", "libelf"),
        required_version = (0, 190),
        compare = VersionCompare.GEQ,
      ),
      DependencyVersionRequirement(
        name = "libssl-dev",
        cmd = ("pkg-config", "--modversion", "libssl"),
        required_version = (3, 0, 13),
        compare = VersionCompare.GEQ,
      ),
      DependencyVersionRequirement(
        name = "pandas",
        cmd = ("python3", "-c", "import pandas; print(pandas.__version__)"),
        required_version = (2, 1, 4),
        compare = VersionCompare.GEQ,
      ),
      FilesystemPathRequirement(
        name = "repo_root_exists",
        path = repo_root,
        path_type = PathType.DIRECTORY,
      ),
    ]

    for key, ref_path in sorted(self._config.ground_truth_paths.items()):
      reqs.append(
        FilesystemPathRequirement(
          name = f"reference_{key}_exists",
          path = ref_path,
          path_type = PathType.FILE,
        )
      )

    return reqs
