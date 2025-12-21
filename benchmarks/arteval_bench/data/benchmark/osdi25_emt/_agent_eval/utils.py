from pathlib import Path

# TODO: Changed from Path.home(), but not sure why the original used it.
HOME = Path("/home/escapist/system-intelligence-benchmark/benchmarks/arteval_bench/data/benchmark/osdi25_emt")
REPO_DIRS = {"emt": HOME / "emt"}

REFERENCE_PATH = HOME / "_agent_eval" / "refs" / "emt-table-2.ref.json" # TODO: I haven't created and quite understood what is this file for.
RESULTS_PATH = REPO_DIRS["emt"] / "emt-table-2.txt"
SIMILARITY_RATIO = 0.75

# PLACEHOLDER FOR FUTURE CONSTANTS UNTIL NEEDED
# --- CUSTOM LOGGER --- #
import logging
import os
from datetime import datetime

os.makedirs('logs', exist_ok=True)

LOG_FORMAT = '%(asctime)s | %(levelname)s | %(name)s | %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

logger = logging.getLogger("OSDI24-ANVIL-AGENT-EVALUATOR")
logger.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))

logger.addHandler(console_handler)