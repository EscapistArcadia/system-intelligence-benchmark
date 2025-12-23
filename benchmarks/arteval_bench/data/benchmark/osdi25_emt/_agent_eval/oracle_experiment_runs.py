import subprocess
import pandas as pd
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Tuple
from utils import HOME, REPO_DIRS, logger, FIG18_REFERENCE_PATH, FIG18_RESULT_PATH, TOLERANCE

# ./collect_data.sh --output ./data/EMT
# (emt) python ipc_with_inst.py --input ./data/EMT --output ./ipc_stats --thp never
# (emt/VM-Bench/) python ./run_scripts/get_unified_kern_inst_ae.py) --input ./data/EMT --output ./inst_stats --thp never

@dataclass(frozen=True)
class Figure18Result:
  ipc_speedup: float
  e2e_speedup: float
  pgwalk_speedup: float

class OracleExperimentRuns:
  def __init__(self):
    self.figure18_result = None  # type: Optional[Figure18Result]
    self.figure18_reference = None  # type: Optional[Figure18Result]
        
  def run_shell_command(self, cmd: Iterable[str], cwd: Optional[str] = None) -> Tuple[int, str, str]:
    """
    Run a command and return (rc, stdout, stderr) tuple.
    """
    try:
      cp = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=cwd)
      return cp.returncode, cp.stdout or "", cp.stderr or ""
    except FileNotFoundError:
      return 127, "", ""
    
  def run_experiment(self) -> Tuple[bool, str]:
    code, _, _ = self.run_shell_command(["./collect_data.sh", "--output", "./data/EMT"], cwd=REPO_DIRS["emt"])
    if code != 0:
      # logger.error("Data collection failed")
      return False, "Data collection failed"
    return True, ""
    
  def generate_figure18_stat(self) -> Tuple[bool, str]:
    code, _, _ = self.run_shell_command(["python", "ipc_with_inst.py", "--input", "./data/EMT", "--output", "./ipc_stats", "--thp", "never"], cwd=REPO_DIRS["emt"])
    if code != 0:
      return False, "Figure 18 statistics generation failed"
    
    df_radix = pd.read_csv(REPO_DIRS["emt"] / "ipc_stats" / "ipc_unified_never_radix_result.csv")
    df_ecpt = pd.read_csv(REPO_DIRS["emt"] / "ipc_stats" / "ipc_unified_never_ecpt_result.csv")

    ipc_speedup = (df_ecpt["ipc"].mean() / df_radix["ipc"].mean())
    e2e_speedup = (df_radix["total_cycles"].mean() / df_ecpt["total_cycles"].mean())
    pgwalk_speedup = (df_radix["page_walk_latency"].mean() / df_ecpt["page_walk_latency"].mean())

    self.figure18_result = Figure18Result(
      ipc_speedup=ipc_speedup,
      e2e_speedup=e2e_speedup,
      pgwalk_speedup=pgwalk_speedup,
    )

    # print(f"Figure 18 Results:\nIPC Speedup: {ipc_speedup:.4f}\nE2E Speedup: {e2e_speedup:.4f}\nPage Walk Speedup: {pgwalk_speedup:.4f}")
    return True, ""
  
  def load_figure18_reference(self) -> Tuple[bool, str]:
    try:
      # df_ref = pd.read_csv(FIG18_REFERENCE_PATH)
      # ref_ipc_speedup = df_ref["ipc_speedup"].iloc[0]
      # ref_e2e_speedup = df_ref["e2e_speedup"].iloc[0]
      # ref_pgwalk_speedup = df_ref["pgwalk_speedup"].iloc[0]

      self.figure18_reference = Figure18Result(
        ipc_speedup=1.044740928,
        e2e_speedup=1.007018443,
        pgwalk_speedup=1.224302584,
      )
      return True, ""
    except Exception as e:
      return False, f"Failed to load Figure 18 reference: {e}"
    
  def compare_figure18_against_reference(self) -> Tuple[bool, str]:
    if self.figure18_result is None:
      return False, "Figure 18 results not loaded"
    if self.figure18_reference is None:
      return False, "Figure 18 reference not loaded"

    def within_tolerance(measured: float, reference: float) -> bool:
      ratio = measured / reference
      return ratio >= (1 - TOLERANCE) and ratio <= (1 + TOLERANCE)
    
    if not within_tolerance(self.figure18_result.ipc_speedup, self.figure18_reference.ipc_speedup):
      return False, "IPC speedup does not match reference"
    if not within_tolerance(self.figure18_result.e2e_speedup, self.figure18_reference.e2e_speedup):
      return False, "E2E speedup does not match reference"
    if not within_tolerance(self.figure18_result.pgwalk_speedup, self.figure18_reference.pgwalk_speedup):
      return False, "Page walk speedup does not match reference"

    return True, ""

  def run(self) -> bool:
    # if not self.run_experiment():
      # return False
    # ok, why = self.run_experiment()
    # if not ok:
    #   logger.error(why)
    #   return False
    
    ok, why = self.generate_figure18_stat()
    if not ok:
      logger.error(why)
      return False
    
    ok, why = self.load_figure18_reference()
    if not ok:
      logger.error(why)
      return False
    
    ok, why = self.compare_figure18_against_reference()
    if not ok:
      logger.error(why)
      return False
  
if __name__ == "__main__":
  OracleExperimentRuns().run()