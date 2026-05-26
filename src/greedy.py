"""
greedy.py
---------
Coverage-first greedy baseline scheduler.

Algorithm:
    For each (day, shift) ordered by minimum required (highest first):
        While slot is under-covered:
            Select the available worker with the fewest shifts so far
            (tiebreak: prefer senior workers)
            Assign that worker
            If no eligible worker found: slot left uncovered

Properties:
    - O(D * S * W) per scenario — trivially fast
    - Deterministic (fixed ordering)
    - No lookahead: violates C4 (consecutive night-morning rest) implicitly
    - No global optimisation: greedy choices block later slots

This is the 'human dispatcher' baseline: reasonable and fast, but blind
to temporal dependencies and global workload structure.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from src.data_generator import Scenario


@dataclass
class GreedyResult:
    """Output of the greedy scheduler."""
    # assignment[worker_id][day][shift] = True/False
    assignment: Dict[int, Dict[int, Dict[int, bool]]] = field(default_factory=dict)
    shifts_per_worker: Dict[int, int] = field(default_factory=dict)
    coverage: Dict[Tuple[int, int], int] = field(default_factory=dict)
    uncovered_slots: List[Tuple[int, int]] = field(default_factory=list)
    constraint_violations: int = 0  # C4 night-then-morning violations
    feasible: bool = True


def schedule_greedy(scenario: Scenario) -> GreedyResult:
    """
    Run the greedy scheduler on the given scenario.
    Returns a GreedyResult.
    """
    cfg     = scenario.config
    workers = scenario.workers
    W       = cfg.n_workers
    D       = cfg.n_days
    S       = cfg.n_shifts

    # Initialise result
    result = GreedyResult()
    for w in range(W):
        result.assignment[w] = {d: {s: False for s in range(S)} for d in range(D)}
        result.shifts_per_worker[w] = 0

    # Order slots: highest minimum coverage first (ties broken by shift index)
    slot_order = sorted(
        [(d, s) for d in range(D) for s in range(S)],
        key=lambda ds: -cfg.min_coverage[ds[1]]
    )

    for (d, s) in slot_order:
        required = cfg.min_coverage[s]
        assigned_count = 0

        # Build candidate pool: available workers not already at max, not already assigned this slot
        # Sort by: shifts_so_far ascending, then tier descending (seniors preferred as tiebreak)
        for _ in range(required):
            candidates = [
                w for w in range(W)
                if (workers[w].availability[d][s]
                    and not result.assignment[w][d][s]
                    and result.shifts_per_worker[w] < cfg.max_shifts_per_week)
            ]

            if not candidates:
                # Slot goes uncovered — greedy cannot backtrack
                break

            # Sort: fewest shifts first, seniors preferred on tie
            candidates.sort(key=lambda w: (result.shifts_per_worker[w], -workers[w].tier))
            chosen = candidates[0]
            result.assignment[chosen][d][s] = True
            result.shifts_per_worker[chosen] += 1
            assigned_count += 1

        result.coverage[(d, s)] = assigned_count
        if assigned_count < required:
            result.uncovered_slots.append((d, s))

    # Count C4 violations (night-then-morning) — greedy doesn't enforce this
    NIGHT   = S - 1
    MORNING = 0
    for w in range(W):
        for d in range(D - 1):
            if (result.assignment[w][d][NIGHT]
                    and result.assignment[w][d + 1][MORNING]):
                result.constraint_violations += 1

    result.feasible = len(result.uncovered_slots) == 0
    return result


def print_greedy_summary(scenario: Scenario, result: GreedyResult) -> None:
    """Print a compact greedy result summary."""
    cfg = scenario.config
    spw = list(result.shifts_per_worker.values())
    print(f"\n  Greedy  [{'FEASIBLE' if result.feasible else 'PARTIAL'}]")
    print(f"  Shifts/worker: mean={sum(spw)/len(spw):.2f}  "
          f"max={max(spw)}  min={min(spw)}  σ={_std(spw):.2f}")
    total_slots = cfg.n_days * cfg.n_shifts
    covered = total_slots - len(result.uncovered_slots)
    print(f"  Coverage met: {covered}/{total_slots} slots "
          f"({100*covered/total_slots:.1f}%)")
    if result.constraint_violations:
        print(f"  C4 violations (night→morning): {result.constraint_violations}")


def _std(values) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    return (sum((v - mean)**2 for v in values) / n) ** 0.5
