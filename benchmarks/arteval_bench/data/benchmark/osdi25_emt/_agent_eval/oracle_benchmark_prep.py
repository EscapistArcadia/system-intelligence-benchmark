"""Benchmark preparation oracle for EGWALKER (EuroSys'25).

Validates:
  - Dataset manifest JSON is readable and well-formed.
  - Each referenced dataset file is within the repo root (no traversal).
  - Each referenced dataset file exists and matches the expected size in bytes.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Mapping, Sequence, Any

from evaluator import utils
from evaluator.utils import EntryConfig
from evaluator.oracle_benchmark_prep_primitives import (
    BenchmarkRequirement,
    FailRequirement,
    OracleBenchmarkPrepBase,
)


def _is_within(root: Path, candidate: Path) -> bool:
  """Returns True iff candidate is within root after (non-strict) resolution.

  Uses resolution to collapse '..' and resolve symlinks in existing parents
  (as much as possible without requiring the final path to exist).
  """
  root_resolved = root.resolve(strict=False)
  cand_resolved = candidate.resolve(strict=False)
  try:
    cand_resolved.relative_to(root_resolved)
    return True
  except ValueError:
    return False


class OracleBenchmarkPrep(OracleBenchmarkPrepBase):
  """Validates dataset prerequisites for _agent_eval bundles."""

  def __init__(
      self,
      *,
      config: EntryConfig,
      logger: logging.Logger,
    #   manifest_key: str = "datasets",
  ) -> None:
    super().__init__(logger=logger)
    self._config = config
    # self._manifest_key = manifest_key

  def requirements(self) -> Sequence[utils.BaseRequirement]:
    reqs: list[utils.BaseRequirement] = []

    required_repo_paths = ["figure16_never", "figure16_always", "figure18"]

    def _load_ref(ref : str):
      path = self._config.ground_truth_paths.get(ref)
      if path is None:
        reqs.append(
          FailRequirement(
              name=f"config:ref:{ref}",
              message=(
                  f"Missing ground_truth_paths[{ref!r}] in EntryConfig"
              ),
          )
        )
        return None
      
      reqs.append(BenchmarkRequirement(name=f"ref:{ref}_exists", filepath=path))
      
      if not path.exists():
        return None
      
      try:
        obj: Any = json.loads(path.read_text(encoding="utf-8"))
        return obj
      except (OSError, json.JSONDecodeError) as exc:
        reqs.append(
          FailRequirement(
              name=f"ref:{ref}_readable",
              message=f"ref unreadable: {exc}",
          )
        )
        return None
      
    for ref in required_repo_paths:
      if _load_ref(ref) is None:
        # If any required reference is missing/unreadable, we can skip the rest of the checks since they likely depend on the reference data.
        break
      
    return reqs

    # TODO: Do we need to check the existence of the kernel image?
    # TODO: Do we really need to read these files in this stage?
    # repo_root = self._config.repository_paths.get(self._config.name)
    # if repo_root is None:
    #   return [
    #       FailRequirement(
    #           name="config:repo_root",
    #           message=(
    #               f"Missing repository_paths[{self._config.name!r}] in EntryConfig"
    #           ),
    #       )
    #   ]

    # # Always report repo root existence as a normal requirement
    # reqs.append(BenchmarkRequirement(name="repo_root_exists", filepath=repo_root))

    # figure16_never_ref_path = self._config.ground_truth_paths.get("figure16_never")
    # if figure16_never_ref_path is None:
    #   reqs.append(
    #       FailRequirement(
    #           name="config:figure16_never_ref",
    #           message=(
    #               f"Missing ground_truth_paths[{self._manifest_key!r}] in EntryConfig"
    #           ),
    #       )
    #   )
    #   return reqs

    # reqs.append(
    #     BenchmarkRequirement(name="figure16_never_ref_exists", filepath=figure16_never_ref_path)
    # )

    # if not figure16_never_ref_path.exists():
    #   return reqs

    # try:
    #   obj: Any = json.loads(figure16_never_ref_path.read_text(encoding="utf-8"))
    # except (OSError, json.JSONDecodeError) as exc:
    #   reqs.append(
    #       FailRequirement(
    #           name="dataset_manifest_readable",
    #           message=f"manifest unreadable: {exc}",
    #       )
    #   )
    #   return reqs

    # if not isinstance(obj, dict):
    #   reqs.append(
    #       FailRequirement(
    #           name="dataset_manifest_format",
    #           message="manifest JSON must be a dictionary",
    #       )
    #   )
    #   return reqs

    # NOTE (Shanbo): Different from egwalker, all data has been presented in the json, so we don't need any extra manipulation or checks for additional files.
    # # Portable size check -- prints a stable marker for signature matching
    # size_script = (
    #     "import os, sys\n"
    #     "p = sys.argv[1]\n"
    #     "print(f'OK size = {os.path.getsize(p)}')\n"
    # )

    # for i, entry in enumerate(obj):
    #   entry_name = f"entry[{i}]"

    #   if not isinstance(entry, dict):
    #     reqs.append(FailRequirement(name=entry_name, message="entry must be an object"))
    #     continue

    #   filepath = entry.get("filepath")
    #   size = entry.get("sizeinbytes")

    #   if not isinstance(filepath, str) or not filepath.strip():
    #     reqs.append(FailRequirement(name=entry_name, message="missing/invalid filepath"))
    #     continue
    #   if not isinstance(size, int) or size < 0:
    #     reqs.append(
    #         FailRequirement(
    #             name=entry_name,
    #             message=f"{filepath!r}: missing/invalid sizeinbytes",
    #         )
    #     )
    #     continue

    #   rel = Path(filepath)

    #   # Disallow absolute paths up-front
    #   if rel.is_absolute():
    #     reqs.append(
    #         FailRequirement(
    #             name=f"dataset:{filepath}",
    #             message="absolute paths not allowed",
    #         )
    #     )
    #     continue

    #   full_path = repo_root / rel

    #   # Enforce containment (prevents '..' traversal / symlink escapes where resolvable)
    #   if not _is_within(repo_root, full_path):
    #     reqs.append(
    #         FailRequirement(
    #             name=f"dataset:{filepath}",
    #             message="path escapes repo root (.. traversal not allowed)",
    #         )
    #     )
    #     continue

    #   # NOTE: Existance is handled by BenchmarkRequirement(filepath=...), but 
    #   # size matching is handled by cmd+signature
    #   reqs.append(
    #       BenchmarkRequirement(
    #           name=f"dataset:{filepath}",
    #           filepath=full_path,
    #           cmd=(sys.executable, "-c", size_script, str(full_path)),
    #           signature=f"OK size = {size}",
    #           timeout_seconds=30.0,
    #       )
    #   )

    return reqs
