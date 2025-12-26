from pathlib import Path

# TODO: Changed from Path.home(), but not sure why the original used it.
HOME = Path.cwd().parent
REPO_DIRS = {"emt": HOME / "emt"}

FIG18_REFERENCE_PATH = HOME / "_agent_eval" / "refs" / "emt-figure16.ref.csv" # TODO: Fill the paper data to the reference 
FIG18_RESULT_PATH = REPO_DIRS["emt"] / "ipc_stats" / "figure18_results.csv"
TOLERANCE = 0.1

# PLACEHOLDER FOR FUTURE CONSTANTS UNTIL NEEDED
# --- CUSTOM LOGGER --- #
import logging
import os
from datetime import datetime

os.makedirs('logs', exist_ok=True)

LOG_FORMAT = '%(asctime)s | %(levelname)s | %(name)s | %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

logger = logging.getLogger("OSDI25-EMT-AGENT-EVALUATOR")
logger.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))

logger.addHandler(console_handler)