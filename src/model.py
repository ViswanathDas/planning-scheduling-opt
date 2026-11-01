"""
model.py — CP-SAT scheduling model.

Hard constraints (five):
    C1  Minimum coverage >= N_min workers per slot
    C2  Maximum coverage <= N_max workers per slot
    C3  Worker availability
    C4  No night-then-morning (rest requirement)
    C5  Max shifts per rolling 7-day window

Objective (minimise):
    5 * total_shifts + 10 * (max_assigned - min_assigned) - preference_total
    Optionally + 100 * total_shortfall when soft_coverage=True
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from ortools.sat.python import cp_model
from src.data_generator import Scenario


@dataclass
class ScheduleResult:
    solver_status: str
    wall_time_s: float
    objective_value: Optional[float]
    assignment: Dict[int, Dict[int, Dict[int, bool]]] = field(default_factory=dict)
    shifts_per_worker: Dict[int, int] = field(default_factory=dict)
    coverage: Dict[Tuple[int, int], int] = field(default_factory=dict)
    feasible: bool = False


def solve(scenario: Scenario, time_limit_s: float = 30.0,
          num_workers_parallel: int = 4, soft_coverage: bool = False) -> ScheduleResult:
    cfg     = scenario.config
    workers = scenario.workers
    W, D, S = cfg.n_workers, cfg.n_days, cfg.n_shifts

    model  = cp_model.CpModel()
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_s
    solver.parameters.num_search_workers  = num_workers_parallel
    solver.parameters.log_search_progress = False

    x = {}
    for w in range(W):
        for d in range(D):
            for s in range(S):
                x[(w, d, s)] = model.NewBoolVar(f"x_{w}_{d}_{s}")

    # C3 — Availability
    for w in range(W):
        for d in range(D):
            for s in range(S):
                if not workers[w].availability[d][s]:
                    model.Add(x[(w, d, s)] == 0)

    # C1 — Coverage (hard or soft)
    shortfall_terms = []
    for d in range(D):
        for s in range(S):
            assigned_ds = sum(x[(w, d, s)] for w in range(W))
            if soft_coverage:
                sf = model.NewIntVar(0, cfg.min_coverage[s], f"sf_{d}_{s}")
                model.Add(assigned_ds + sf >= cfg.min_coverage[s])
                shortfall_terms.append(sf)
            else:
                model.Add(assigned_ds >= cfg.min_coverage[s])

    # C2 — Max coverage
    for d in range(D):
        for s in range(S):
            model.Add(sum(x[(w, d, s)] for w in range(W)) <= cfg.max_coverage)

    # C4 — No night-then-morning
    for w in range(W):
        for d in range(D - 1):
            model.Add(x[(w, d, S-1)] + x[(w, d+1, 0)] <= 1)

    # C5 — Max shifts in every rolling 7-day window (days start..start+6)
    window = min(7, D)
    for w in range(W):
        for start in range(0, D - window + 1):
            model.Add(sum(x[(w, d, s)] for d in range(start, start + window) for s in range(S))
                      <= cfg.max_shifts_per_week)

    # Per-worker IntVars for AddMaxEquality/AddMinEquality
    assigned_vars = []
    for w in range(W):
        a_w = model.NewIntVar(0, D*S, f"a_{w}")
        model.Add(a_w == sum(x[(w, d, s)] for d in range(D) for s in range(S)))
        assigned_vars.append(a_w)

    max_a = model.NewIntVar(0, D*S, "max_a")
    min_a = model.NewIntVar(0, D*S, "min_a")
    model.AddMaxEquality(max_a, assigned_vars)
    model.AddMinEquality(min_a, assigned_vars)

    total_shifts = sum(x[(w, d, s)] for w in range(W) for d in range(D) for s in range(S))
    preference   = sum(workers[w].preference[d][s] * x[(w, d, s)]
                       for w in range(W) for d in range(D) for s in range(S))
    obj = 5 * total_shifts + 10 * (max_a - min_a) - preference
    if shortfall_terms:
        obj = obj + 100 * sum(shortfall_terms)
    model.Minimize(obj)

    status_code = solver.Solve(model)
    STATUS_MAP = {cp_model.OPTIMAL:"OPTIMAL", cp_model.FEASIBLE:"FEASIBLE",
                  cp_model.INFEASIBLE:"INFEASIBLE", cp_model.MODEL_INVALID:"MODEL_INVALID",
                  cp_model.UNKNOWN:"UNKNOWN"}
    status_str = STATUS_MAP.get(status_code, str(status_code))
    feasible   = status_code in (cp_model.OPTIMAL, cp_model.FEASIBLE)

    result = ScheduleResult(solver_status=status_str, wall_time_s=solver.WallTime(),
                            objective_value=solver.ObjectiveValue() if feasible else None,
                            feasible=feasible)
    if not feasible:
        return result

    for w in range(W):
        result.assignment[w] = {}
        total = 0
        for d in range(D):
            result.assignment[w][d] = {}
            for s in range(S):
                val = bool(solver.Value(x[(w, d, s)]))
                result.assignment[w][d][s] = val
                total += int(val)
        result.shifts_per_worker[w] = total

    for d in range(D):
        for s in range(S):
            result.coverage[(d, s)] = sum(int(result.assignment[w][d][s]) for w in range(W))
    return result


def print_result_summary(scenario: Scenario, result: ScheduleResult) -> None:
    cfg = scenario.config
    print(f"  CP-SAT  [{result.solver_status}]  time={result.wall_time_s*1000:.0f}ms  obj={result.objective_value}")
    if not result.feasible:
        return
    spw = list(result.shifts_per_worker.values())
    mean = sum(spw)/len(spw)
    std  = (sum((v-mean)**2 for v in spw)/len(spw))**0.5
    print(f"  Shifts/worker: mean={mean:.2f}  max={max(spw)}  min={min(spw)}  sigma={std:.2f}")
    slots_met = sum(1 for (d,s),cnt in result.coverage.items() if cnt >= cfg.min_coverage[s])
    print(f"  Coverage met: {slots_met}/{cfg.n_days*cfg.n_shifts} slots ({100*slots_met/(cfg.n_days*cfg.n_shifts):.1f}%)")
