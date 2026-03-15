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


def _required_path(paths: Mapping[str, Path], key: str, *, label: str) -> Path:
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


def _as_float(v: object, *, label: str) -> float:
  """Converts numeric values to float; raises on non-numeric."""
  if isinstance(v, (int, float)):
    return float(v)
  raise ValueError(f"{label}: non-numeric value {v!r}")


def _iter_metric_tag_rows(
  obj: object, *, label: str
) -> Iterable[tuple[str, Mapping[str, object]]]:
  """Yields (row_key, stats_dict) where row_key is '<metric>.<tag>'."""
  if not isinstance(obj, dict):
    raise ValueError(f"{label}: timings JSON must be an object at top-level")

  for metric_name, metric in obj.items():
    if not isinstance(metric_name, str):
      raise ValueError(f"{label}: non-string metric name {metric_name!r}")
    if not isinstance(metric, dict):
      raise ValueError(f"{label}: {metric_name!r} must map to an object")

    for tag, stats in metric.items():
      if not isinstance(tag, str):
        raise ValueError(f"{label}: non-string tag name {tag!r}")
      if not isinstance(stats, dict):
        raise ValueError(f"{label}: {metric_name}.{tag} must map to an object")

      row_key = f"{metric_name}.{tag}"
      yield row_key, stats


def _discover_reference_fields(reference_obj: object, *, label: str) -> tuple[str, ...]:
  """Returns unique stats fields in order of first appearance in the reference."""
  seen: set[str] = set()
  ordered: list[str] = []
  for _row_key, stats in _iter_metric_tag_rows(reference_obj, label=label):
    for field in stats.keys():
      if not isinstance(field, str):
        raise ValueError(f"{label}: non-string field name {field!r}")
      if field not in seen:
        seen.add(field)
        ordered.append(field)
  return tuple(ordered)


def _values_by_label_for_field(
  obj: object,
  *,
  field: str | None,
  label: str,
) -> dict[str, float]:
  """Extracts timing values keyed by stable labels.

  If field is not None:
   - label is '<metric>.<tag>'
   - value is stats[field]
   - rows missing the field are skipped (so the *reference* defines expectation)

  If field is None (flatten):
   - label is '<metric>.<tag>.<field>'
   - value is stats[field]
  """
  out: dict[str, float] = {}
  for row_key, stats in _iter_metric_tag_rows(obj, label=label):
    if field is None:
      for f, raw in stats.items():
        if not isinstance(f, str):
          raise ValueError(f"{label}: non-string field name {f!r}")
        k = f"{row_key}.{f}"
        if k in out:
          raise ValueError(f"{label}: duplicate label {k!r}")
        out[k] = _as_float(raw, label=f"{label}: {k}")
    else:
      if field not in stats:
        continue
      if row_key in out:
        raise ValueError(f"{label}: duplicate label {row_key!r}")
      out[row_key] = _as_float(stats[field], label=f"{label}: {row_key}.{field}")
  return out


def _format_missing_labels(missing: Sequence[str], *, max_items: int = 10) -> str:
  if not missing:
    return ""
  head = list(missing[:max_items])
  more = len(missing) - len(head)
  suffix = f"\n... ({more} more)" if more > 0 else ""
  return "missing labels:\n" + "\n".join(f"- {k}" for k in head) + suffix


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class TimingsJSONSimilarityRequirement(utils.BaseRequirement):
  """Artifact-specific wrapper that delegates numeric checks to base primitives."""

  results_path: Path
  reference_path: Path
  threshold: float
  field: str | None = None 
  abs_epsilon: float = 1e-12
  max_mismatches_to_report: int = 10

  def check(self, ctx: ExperimentRunsContext) -> utils.CheckResult:
    try:
      results_obj = _load_json_file(self.results_path, label="timings results")
      reference_obj = _load_json_file(self.reference_path, label="timings reference")

      ref_map = _values_by_label_for_field(
        reference_obj, field=self.field, label="timings reference"
      )
      res_map = _values_by_label_for_field(
        results_obj, field=self.field, label="timings results"
      )

      expected_labels = sorted(ref_map.keys())
      missing = [k for k in expected_labels if k not in res_map]
      if missing:
        detail = _format_missing_labels(missing, max_items=self.max_mismatches_to_report)
        msg = f"{self.name}: results missing required reference entries"
        if detail:
          msg = f"{msg}\n{detail}"
        return utils.CheckResult.failure(msg)

      observed = [res_map[k] for k in expected_labels]
      reference = [ref_map[k] for k in expected_labels]
    except ValueError as exc:
      return utils.CheckResult.failure(f"{self.name}: {exc}")

    delegated = ListSimilarityRequirement(
      name=self.name,
      optional=self.optional,
      observed=observed,
      reference=reference,
      metric=SimilarityMetric.PEARSON,
      min_similarity=self.threshold,  # reuse the same config knob
    )
    return delegated.check(ctx)

@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Figure16NeverRequirement(utils.BaseRequirement):
  """Artifact-specific wrapper that delegates numeric checks to base primitives."""
  results_path: Path
  reference_path: Path
  threshold: float
  # system: str | None = None # radix vs ecpt
  # function: str | None = None

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
    # figure_18_never_results_path = _required_path(self._config.results_paths, "figure18_never", label="results_paths")
    # figure_18_never_reference_path = _required_path(
    #   self._config.ground_truth_paths, "figure18_never", label="ground_truth_paths"
    # )

    threshold = self._config.similarity_ratio

    reqs: list[utils.BaseRequirement] = [
      Figure16NeverRequirement(
        name="figure16_never",
        results_path=figure16_never_results_path,
        reference_path=figure16_never_reference_path,
        threshold=threshold,
      ),
      # Figure18NeverRequirement(
      #   name="figure18_never",
      #   results_path=figure_18_never_results_path,
      #   reference_path=figure_18_never_reference_path,
      #   threshold=threshold,
      # ),
    ]

    # Discover which fields to check from the reference.
    # try:
    #   figure16_never_ref_obj = _load_json_file(figure16_never_reference_path, label="timings reference")
    #   figure16_never_fields = _discover_reference_fields(figure16_never_ref_obj, label="timings reference")
    # except ValueError:
    #   figure16_never_fields = ()

    # if not figure16_never_fields:
    #   # Fallback: compare all fields flattened.
    #   return (
    #     TimingsJSONSimilarityRequirement(
    #       name="figure16_never",
    #       results_path=figure16_never_results_path,
    #       reference_path=figure16_never_reference_path,
    #       threshold=threshold,
    #       field=None,
    #     ),
    #   )
    
    # try:
    #   figure18_never_ref_obj = _load_json_file(figure_18_never_reference_path, label="timings reference")
    #   figure18_never_fields = _discover_reference_fields(figure18_never_ref_obj, label="timings reference")
    # except ValueError:
    #   figure18_never_fields = ()

    # if not figure18_never_fields:
    #   # Fallback: compare all fields flattened.
    #   return (
    #     TimingsJSONSimilarityRequirement(
    #       name="figure18_never",
    #       results_path=figure_18_never_results_path,
    #       reference_path=figure_18_never_reference_path,
    #       threshold=threshold,
    #       field=None,
    #     ),
    #   )

    # reqs: list[utils.BaseRequirement] = []
    # for field in figure16_never_fields:
    #   reqs.append(
    #     TimingsJSONSimilarityRequirement(
    #       name=f"figure16_never_{field}",
    #       results_path=figure16_never_results_path,
    #       reference_path=figure16_never_reference_path,
    #       threshold=threshold,
    #       field=field,
    #     )
    #   )

    # for field in figure18_never_fields:
    #   reqs.append(
    #     TimingsJSONSimilarityRequirement(
    #       name=f"figure18_never_{field}",
    #       results_path=figure_18_never_results_path,
    #       reference_path=figure_18_never_reference_path,
    #       threshold=threshold,
    #       field=field,
    #     )
    #   )
    return tuple(reqs)
