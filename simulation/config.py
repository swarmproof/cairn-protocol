"""Configuration for the CAIRN recovery score calibration simulation."""

from dataclasses import dataclass, field

# Failure class definitions
FAILURE_CLASSES = ["LIVENESS", "RESOURCE", "LOGIC"]
FAILURE_CLASS_DISTRIBUTION = {"LIVENESS": 0.45, "RESOURCE": 0.35, "LOGIC": 0.20}

# Current CAIRN parameters (whitepaper V2, Equation 1)
DEFAULT_WEIGHTS = (0.5, 0.3, 0.2)  # (w_f, w_b, w_d)
DEFAULT_CLASS_WEIGHTS = {"LIVENESS": 0.9, "RESOURCE": 0.5, "LOGIC": 0.1}
DEFAULT_UPPER_THRESHOLD = 0.6
DEFAULT_LOWER_THRESHOLD = 0.3

# Ground truth base recovery rates (from MAST taxonomy + agent reliability research)
GROUND_TRUTH_BASE_RATES = {"LIVENESS": 0.92, "RESOURCE": 0.48, "LOGIC": 0.08}

# Simulation parameters
SEED = 42
TRIALS_PER_COMBO = 10_000
TOTAL_BASELINE_TRIALS = 100_000

# Task type definitions
TASK_TYPES = [
    "defi.price_fetch",
    "defi.trade_execute",
    "data.report_generate",
    "governance.vote_delegate",
    "compute.model_inference",
]


@dataclass(frozen=True)
class GridSearchConfig:
    """Grid search ranges for weight optimization."""

    w_f_range: tuple = (0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70)
    w_b_range: tuple = (0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40)
    min_w_d: float = 0.05

    f_liveness_range: tuple = (0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00)
    f_resource_range: tuple = (0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60)
    f_logic_range: tuple = (0.00, 0.05, 0.10, 0.15, 0.20)

    upper_range: tuple = (0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80)
    lower_range: tuple = (0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40)
