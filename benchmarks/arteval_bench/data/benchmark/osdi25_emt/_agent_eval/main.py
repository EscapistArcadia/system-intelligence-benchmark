#!/usr/bin/env python3
"""Runs environment setup, build, benchmark prep, and experiment runs checks for EMT (OSDI'25)."""

from __future__ import annotations

from pathlib import Path
from typing import Dict
import os
import sys


_AGENT_EVAL_DIR = Path(__file__).resolve().parent
_AGENT_SRC_DIR = _AGENT_EVAL_DIR.parents[3] / "src"
sys.path.append(str(_AGENT_SRC_DIR))


from evaluator.utils import (
  EntryConfig,
  LoggerConfig,
  get_logger,
  record_result,
)
from oracle_artifact_build import OracleArtifactBuild
from oracle_env_setup import OracleEnvSetup
from oracle_benchmark_prep import OracleBenchmarkPrep
from oracle_experiment_runs import OracleExperimentRuns

def _resolve_workspace_paths() -> tuple[Path, Path, Path]:
  """Resolve and validate _agent_eval/ and emt/ locations.
  This expectes that either:
    (1) _agent_eval/ and emt/ are located in the same root directory; or
    (2) _AGENT_EVAL_DIR and _EMT_HOME are set by the user
  """
  try:
    env_agent_eval = os.environ.get("_AGENT_EVAL_DIR")
    env_emt_home = os.environ.get("_EMT_HOME")
    
    if env_agent_eval:
      agent_eval_dir = Path(env_agent_eval).expanduser().resolve()
    else:
      agent_eval_dir = Path(__file__).resolve().parent

    if env_emt_home:
      emt_home = Path(env_emt_home).expanduser().resolve()
    else:
      emt_home = agent_eval_dir.parent.resolve()

    if not agent_eval_dir.exists() or not agent_eval_dir.is_dir():
      raise RuntimeError(
          f"Invalid _agent_eval dir: {agent_eval_dir}\n"
          f"This runner expects _agent_eval/ and emt/ to be located in the same root directory.\n"
          f"Set _AGENT_EVAL_DIR to the directory containing main.py if needed."
      )

    emt_repo_root = emt_home / "emt"
    if not emt_repo_root.exists() or not emt_repo_root.is_dir():
      raise RuntimeError(
          f"Invalid EMT workspace: {emt_home}\n"
          f"Expected to find a 'emt/' directory at: {emt_repo_root}\n"
          f"This runner expects _agent_eval/ and emt/ to be located in the same root directory.\n"
          f"Set _EMT_HOME to the workspace root if needed."
      )

    workspace_root = emt_home
    return agent_eval_dir, workspace_root

  except OSError as exc:
    raise RuntimeError(f"Failed to resolve workspace paths: {exc}") from exc
  

def _build_emt_config(*, agent_eval_dir: Path, workspace_root: Path) -> EntryConfig:
  """Constructs EntryConfig for the EMT evaluation bundle from resolved paths."""
  emt_repo = (workspace_root / "emt").resolve()
  emt_agent_eval = agent_eval_dir.resolve()
  emt_refs = (emt_agent_eval / "refs").resolve() # TODO: update the actual reference data and paths
  # emt_results = (emt_repo / "results").resolve() # TODO: update the logic to process results

  return EntryConfig(
    name = "osdi25-emt",
    home_dir = workspace_root,
    repository_paths = {
      "osdi25-emt": emt_repo,
    },
    results_paths = {
      "figure16_never" : emt_repo / "inst_stats" / "kern_inst_never_unified.csv",
      # "figure16_always" : emt_repo / "inst_stats" / "kern_inst_always_result.csv", 
      "figure18_never" : {
        "radix" : emt_repo / "ipc_stats" / "ipc_unified_never_radix_result.csv",
        "ecpt" : emt_repo / "ipc_stats" / "ipc_unified_never_ecpt_result.csv",
      },
      # "figure18_always" : {
      #   "radix" : emt_repo / "ipc_stats" / "ipc_unified_always_radix_result.csv",
      #   "ecpt" : emt_repo / "ipc_stats" / "ipc_unified_always_ecpt_result.csv",
      # },
    },
    ground_truth_paths = {
      "figure16_never": emt_refs / "figure16_never.ref.csv",
      # "figure16_always": emt_refs / "figure16_always.ref.json",
      # "figure18_never" : emt_refs / "figure18_never.ref.csv",
    },
    similarity_ratio = 0.75, # TODO: update this threshold based on actual reference data and evaluation criteria
  )

def main(argv: list[str]) -> int:
  verbose = "--verbose" in argv

  results: Dict[str, int] = {}
  score = 0

  logger_name = os.environ.get("EVAL_LOGGER_NAME", "EMT-AGENT-EVALUATOR")
  logger = get_logger(LoggerConfig(root_name = logger_name))

  try:
    agent_eval_dir, workspace_root = _resolve_workspace_paths()
    EMT_CONFIG = _build_emt_config(agent_eval_dir = agent_eval_dir, workspace_root = workspace_root)
  except RuntimeError as exc:
    raise SystemExit(str(exc)) from exc

  env_checker = OracleEnvSetup(config = EMT_CONFIG, logger = logger)
  score += record_result(results, type(env_checker).__name__, env_checker.run(verbose = verbose))

  build_checker = OracleArtifactBuild(config = EMT_CONFIG, logger = logger)
  score += record_result(results, type(build_checker).__name__, build_checker.run(verbose = verbose))

  prep_checker = OracleBenchmarkPrep(config = EMT_CONFIG, logger = logger)
  score += record_result(results, type(prep_checker).__name__, prep_checker.run(verbose = verbose))

  runs_checker = OracleExperimentRuns(config = EMT_CONFIG, logger = logger)
  score += record_result(results, type(runs_checker).__name__, runs_checker.run(verbose = verbose))

  logger.info("Agent scores: %s", results)
  return score


if __name__ == "__main__":
  raise SystemExit(main(sys.argv[1:]))
