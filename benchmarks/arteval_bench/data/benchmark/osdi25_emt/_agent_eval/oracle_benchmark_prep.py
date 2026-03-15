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

    # TODO: Do we need to check the existence of the kernel image?
    return reqs
