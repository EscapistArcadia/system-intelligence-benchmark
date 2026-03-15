"""Experiment runs oracle for EGWALKER (EuroSys'25).

Validates:
 - Timing results file can be read and parsed.
 - Ground-truth reference timings file exists and can be read.
 - Observed timings meet the configured similarity threshold against reference timings.
"""

from __future__ import annotations

import dataclasses
import json
import logging
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any
import pandas as pd

from evaluator import utils
from evaluator.oracle_experiment_runs_primitives import (
  ExperimentRunsContext,
  ListSimilarityRequirement,
  OracleExperimentRunsBase,
  SimilarityMetric,
)
from evaluator.utils import EntryConfig


def _required_path(paths: Mapping[str, Path], key: str, *, label: str):
  """Returns a required path from a mapping with a clear error message."""
  try:
    p = paths[key]
  except KeyError as exc:
    raise ValueError(f"Missing {label}[{key!r}] in EntryConfig") from exc
  return p


def _load_json_file(path: Path, *, label: str) -> object:
  """Loads JSON from a file path with consistent error messages."""
  try:
    text = path.read_text(encoding="utf-8")
  except OSError as exc:
    raise ValueError(f"{label}: failed to read {path}: {exc}") from exc
  text = text.strip()
  if not text:
    raise ValueError(f"{label}: empty JSON content at {path}")
  try:
    return json.loads(text)
  except json.JSONDecodeError as exc:
    raise ValueError(f"{label}: invalid JSON in {path}: {exc}") from exc


def _load_csv_file(path: Path, *, label: str) -> pd.DataFrame:
  """Loads CSV from a file path with consistent error messages."""
  try:
    return pd.read_csv(path)
  except Exception as exc:
    raise ValueError(f"{label}: failed to read CSV {path}: {exc}") from exc


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Figure16Requirement(utils.BaseRequirement):
  """Artifact-specific wrapper that delegates numeric checks to base primitives."""
  results_path: Path
  reference_path: Path
  threshold: float
  # system: str | None = None # radix vs ecpt
  # function: str | None = None
  thp: str | None = None # never vs always

  def check(self, ctx: ExperimentRunsContext) -> utils.CheckResult:
    try:
      df_results = _load_csv_file(self.results_path, label="figure16_never")
      df_reference = _load_csv_file(self.reference_path, label="figure16_never")

      if not df_results.columns.equals(df_reference.columns):
        return utils.CheckResult.failure(
          f"{self.name}: results and reference CSV columns do not match: "
          f"{df_results.columns.tolist()} vs {df_reference.columns.tolist()}"
        )
      
      if df_results.empty or df_reference.empty:
        return utils.CheckResult.failure(
          f"{self.name}: results or reference CSV is empty"
        )
      
      df_results = df_results[df_results["workload"] == "BFS"].set_index(["system", "function"]).sort_index()
      df_reference = df_reference[df_reference["workload"] == "BFS"].set_index(["system", "function"]).sort_index()
      if not df_results.index.equals(df_reference.index):
        return utils.CheckResult.failure(
          f"{self.name}: results and reference CSV indices do not match after filtering to BFS workload: "
          f"{df_results.index.tolist()} vs {df_reference.index.tolist()}"
        )
      
      observed = df_results["instruction"].tolist()
      reference = df_reference["instruction"].tolist()

      delegated = ListSimilarityRequirement(
        name=self.name,
        optional=self.optional,
        observed=observed,
        reference=reference,
        metric=SimilarityMetric.PEARSON,
        min_similarity=self.threshold,
      )
      return delegated.check(ctx)

    except ValueError as exc:
      return utils.CheckResult.failure(f"{self.name}: {exc}")

@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Figure18Requirement(utils.BaseRequirement):
  """Artifact-specific wrapper that delegates numeric checks to base primitives."""
  results_path_radix: Path
  results_path_ecpt: Path
  reference_path: Path
  threshold: float
  # system: str | None = None # radix vs ecpt
  # function: str | None = None
  thp: str | None = None # never vs always

  def check(self, ctx: ExperimentRunsContext) -> utils.CheckResult:
    try:
      df_results_radix = _load_csv_file(self.results_path_radix, label="figure18_radix")
      df_results_ecpt = _load_csv_file(self.results_path_ecpt, label="figure18_ecpt")
      json_reference = _load_json_file(self.reference_path, label="figure18_never")

      if not df_results_radix.columns.equals(df_results_ecpt.columns):
        return utils.CheckResult.failure(
          f"{self.name}: radix and ecpt results CSV columns do not match: "
          f"{df_results_radix.columns.tolist()} vs {df_results_ecpt.columns.tolist()}"
        )
      
      if df_results_radix.empty or df_results_ecpt.empty or json_reference is None:
        return utils.CheckResult.failure(
          f"{self.name}: results or reference is invalid"
        )

      result_ipc_speedup = df_results_ecpt["ipc"].mean() / df_results_radix["ipc"].mean()
      result_e2e_speedup = df_results_radix["total_cycles"].mean() / df_results_ecpt["total_cycles"].mean()
      result_pgwalk_speedup = df_results_radix["page_walk_latency"].mean() / df_results_ecpt["page_walk_latency"].mean()
      
      observed = [
        df_results_ecpt["ipc"].mean() / df_results_radix["ipc"].mean(), # IPC speedup
        df_results_radix["total_cycles"].mean() / df_results_ecpt["total_cycles"].mean(), # E2E speedup
        df_results_radix["page_walk_latency"].mean() / df_results_ecpt["page_walk_latency"].mean(), # Page walk speedup
      ]
      reference = [
        json_reference["ipc_speedup"],
        json_reference["e2e_speedup"],
        json_reference["pgwalk_speedup"],
      ]

      delegated = ListSimilarityRequirement(
        name=self.name,
        optional=self.optional,
        observed=observed,
        reference=reference,
        metric=SimilarityMetric.PEARSON,
        min_similarity=self.threshold,
      )
      return delegated.check(ctx)

    except ValueError as exc:
      return utils.CheckResult.failure(f"{self.name}: {exc}")

class OracleExperimentRuns(OracleExperimentRunsBase):
  """Validates experiment run timings."""

  def __init__(self, *, config: EntryConfig, logger: logging.Logger) -> None:
    super().__init__(logger=logger)
    self._config = config

  def requirements(self) -> Sequence[utils.BaseRequirement]:
    if not self._config.results_paths:
      raise ValueError("EntryConfig.results_paths must be non-empty")
    if not self._config.ground_truth_paths:
      raise ValueError("EntryConfig.ground_truth_paths must be non-empty")

    figure16_never_results_path = _required_path(self._config.results_paths, "figure16_never", label="results_paths")
    figure16_never_reference_path = _required_path(
      self._config.ground_truth_paths, "figure16_never", label="ground_truth_paths"
    )
    figure_18_never_results_path = _required_path(self._config.results_paths, "figure18_never", label="results_paths")
    figure_18_never_results_path_radix = figure_18_never_results_path["radix"]
    figure_18_never_results_path_ecpt = figure_18_never_results_path["ecpt"]
    figure_18_never_reference_path = _required_path(
      self._config.ground_truth_paths, "figure18_never", label="ground_truth_paths"
    )

    threshold = self._config.similarity_ratio

    reqs: list[utils.BaseRequirement] = [
      Figure16Requirement(
        name="figure16_never",
        results_path=figure16_never_results_path,
        reference_path=figure16_never_reference_path,
        threshold=threshold,
        thp="never",
      ),
      Figure18Requirement(
        name="figure18_never",
        results_path_radix=figure_18_never_results_path_radix,
        results_path_ecpt=figure_18_never_results_path_ecpt,
        reference_path=figure_18_never_reference_path,
        threshold=threshold,
      ),
    ]
    
    return tuple(reqs)
