"""
data_generator.py
-----------------
Generates self-contained scheduling scenario datasets.
All scenarios are deterministic given a fixed seed — reproducible
and independent of any external data source.

Three scenarios:
    A — Baseline      : 12 workers, 7 days, moderate availability (seed 42)
    B — Tight         : 12 workers, 7 days, high unavailability (seed 7)
    C — Hard / Scaled : 20 workers, 14 days, high demand (seed 99)
"""

from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Dict, List

SHIFT_NAMES = ["Morning", "Afternoon", "Night"]
TIER_NAMES  = {0: "Junior", 1: "Senior"}


@dataclass
class Worker:
    id: int
    name: str
    tier: int          # 0 = junior, 1 = senior
    # availability[day][shift] = True if worker is available
    availability: Dict[int, Dict[int, bool]] = field(default_factory=dict)
    # preference[day][shift] = integer 0-3 (higher = prefers this slot)
    preference: Dict[int, Dict[int, int]] = field(default_factory=dict)


@dataclass
class ScenarioConfig:
    name: str
    description: str
    n_workers: int
    n_senior: int
    n_days: int
    n_shifts: int               # shifts per day (always 3 in this study)
    unavailability_rate: float  # fraction of slots each worker is unavailable
    min_coverage: Dict[int, int]  # shift_index -> minimum workers required
    max_coverage: int
    max_shifts_per_week: int    # upper bound on shifts per worker per week
    seed: int


@dataclass
class Scenario:
    config: ScenarioConfig
    workers: List[Worker]

    @property
    def n_workers(self): return len(self.workers)
    @property
    def n_days(self):    return self.config.n_days
    @property
    def n_shifts(self):  return self.config.n_shifts


# ── Preset scenario configurations ──────────────────────────────────────────

SCENARIO_CONFIGS: Dict[str, ScenarioConfig] = {
    "A": ScenarioConfig(
        name="A — Baseline",
        description="12 workers, 7 days, 20% unavailability — both solvers should find feasible solutions",
        n_workers=12,
        n_senior=4,
        n_days=7,
        n_shifts=3,
        unavailability_rate=0.20,
        min_coverage={0: 3, 1: 2, 2: 2},   # morning=3, afternoon=2, night=2
        max_coverage=5,
        max_shifts_per_week=5,
        seed=42,
    ),
    "B": ScenarioConfig(
        name="B — Tight Availability",
        description="12 workers, 7 days, 40% unavailability — greedy struggles; CP-SAT finds feasible solution",
        n_workers=12,
        n_senior=4,
        n_days=7,
        n_shifts=3,
        unavailability_rate=0.40,
        min_coverage={0: 3, 1: 2, 2: 2},
        max_coverage=5,
        max_shifts_per_week=5,
        seed=7,
    ),
    "C": ScenarioConfig(
        name="C — Hard / Scaled",
        description="20 workers, 14 days, higher demand — demonstrates solver scaling and efficiency gains",
        n_workers=20,
        n_senior=6,
        n_days=14,
        n_shifts=3,
        unavailability_rate=0.30,
        min_coverage={0: 4, 1: 3, 2: 3},   # morning=4, afternoon=3, night=3
        max_coverage=7,
        max_shifts_per_week=8,              # 14-day window, so higher cap
        seed=99,
    ),
}


# ── Generator ────────────────────────────────────────────────────────────────

def generate_scenario(config_key: str) -> Scenario:
    """
    Generate a scheduling scenario from a preset config key ("A", "B", or "C").
    Returns a Scenario with fully populated Worker objects.
    """
    cfg = SCENARIO_CONFIGS[config_key]
    rng = random.Random(cfg.seed)

    # Assign tiers: first n_senior workers are senior, rest junior
    workers = []
    for w in range(cfg.n_workers):
        tier = 1 if w < cfg.n_senior else 0
        name = f"W{w:02d}_{'Sr' if tier else 'Jr'}"

        availability: Dict[int, Dict[int, bool]] = {}
        preference: Dict[int, Dict[int, int]] = {}

        for d in range(cfg.n_days):
            availability[d] = {}
            preference[d] = {}
            for s in range(cfg.n_shifts):
                # Worker is unavailable with probability = unavailability_rate
                avail = rng.random() >= cfg.unavailability_rate
                availability[d][s] = avail

                # Preference: random integer 0-3, only for available slots
                pref = rng.randint(0, 3) if avail else 0
                preference[d][s] = pref

        workers.append(Worker(id=w, name=name, tier=tier,
                               availability=availability, preference=preference))

    return Scenario(config=cfg, workers=workers)


def print_scenario_summary(scenario: Scenario) -> None:
    """Print a compact summary of a scenario to stdout."""
    cfg = scenario.config
    total_slots = cfg.n_days * cfg.n_shifts
    print(f"\n{'='*60}")
    print(f"Scenario {cfg.name}")
    print(f"  {cfg.description}")
    print(f"  Workers : {cfg.n_workers} ({cfg.n_senior} senior, "
          f"{cfg.n_workers - cfg.n_senior} junior)")
    print(f"  Days    : {cfg.n_days}   Shifts/day: {cfg.n_shifts}")
    print(f"  Coverage: morning≥{cfg.min_coverage[0]}, "
          f"afternoon≥{cfg.min_coverage[1]}, night≥{cfg.min_coverage[2]}")
    print(f"  Unavail : {cfg.unavailability_rate*100:.0f}% per worker per slot")

    # Compute actual availability stats
    total_avail = sum(
        scenario.workers[w].availability[d][s]
        for w in range(cfg.n_workers)
        for d in range(cfg.n_days)
        for s in range(cfg.n_shifts)
    )
    total_possible = cfg.n_workers * total_slots
    print(f"  Actual availability: {100*total_avail/total_possible:.1f}% of worker-slots")
    print(f"{'='*60}")
