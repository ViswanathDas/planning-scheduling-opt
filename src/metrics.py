from __future__ import annotations
import math
from typing import Dict, List, Tuple
from src.data_generator import Scenario
from src.greedy import GreedyResult
from src.model import ScheduleResult


def _std(values):
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    return math.sqrt(sum((v - mean)**2 for v in values) / n)


def coverage_rate(scenario, coverage):
    cfg = scenario.config
    met = sum(1 for (d, s), cnt in coverage.items() if cnt >= cfg.min_coverage[s])
    return met / (cfg.n_days * cfg.n_shifts)


def total_shifts(shifts_per_worker):
    return sum(shifts_per_worker.values())


def workload_imbalance(shifts_per_worker):
    vals = list(shifts_per_worker.values())
    return {"std": _std(vals), "range": max(vals) - min(vals),
            "max": max(vals), "min": min(vals), "mean": sum(vals) / len(vals)}


def compare(scenario, greedy, cpsat):
    g_cov   = coverage_rate(scenario, greedy.coverage)
    g_total = total_shifts(greedy.shifts_per_worker)
    g_imbal = workload_imbalance(greedy.shifts_per_worker)
    c_cov   = coverage_rate(scenario, cpsat.coverage) if cpsat.feasible else None
    c_total = total_shifts(cpsat.shifts_per_worker)   if cpsat.feasible else None
    c_imbal = workload_imbalance(cpsat.shifts_per_worker) if cpsat.feasible else None

    shift_red = (100.0 * (g_total - c_total) / g_total
                 if c_total is not None and g_total > 0 else None)
    imbal_red = (100.0 * (g_imbal["std"] - c_imbal["std"]) / g_imbal["std"]
                 if c_imbal is not None and g_imbal["std"] > 0 else None)

    return {
        "scenario": scenario.config.name,
        "greedy": {
            "coverage_rate":   g_cov,
            "total_shifts":    g_total,
            "imbalance":       g_imbal,
            "uncovered_slots": len(greedy.uncovered_slots),
            "c4_violations":   greedy.constraint_violations,
            "feasible":        greedy.feasible,
        },
        "cpsat": {
            "coverage_rate": c_cov,
            "total_shifts":  c_total,
            "imbalance":     c_imbal,
            "solver_status": cpsat.solver_status,
            "wall_time_s":   cpsat.wall_time_s,
            "feasible":      cpsat.feasible,
        },
        "improvement": {
            "shift_reduction_pct":     shift_red,
            "imbalance_reduction_pct": imbal_red,
            "coverage_gap": (c_cov - g_cov) if c_cov is not None else None,
        },
    }


def _fmt(val, spec=".2f"):
    return "n/a" if val is None else format(val, spec)


def print_comparison_table(comp):
    g   = comp["greedy"]
    c   = comp["cpsat"]
    imp = comp["improvement"]
    hr  = "-" * 62

    g_cov_s = "{:.1f}%".format(g["coverage_rate"] * 100)
    c_cov_s = "{:.1f}%".format(c["coverage_rate"] * 100) if c["coverage_rate"] is not None else "n/a"
    c_tot_s = str(c["total_shifts"]) if c["total_shifts"] is not None else "n/a"
    c_std_s = _fmt(c["imbalance"]["std"] if c["imbalance"] else None)
    c_max_s = _fmt(c["imbalance"]["max"] if c["imbalance"] else None, "d")
    c_unc_s = "0" if c["feasible"] else "n/a"
    c_c4_s  = "0" if c["feasible"] else "n/a"

    print()
    print(hr)
    print("  " + comp["scenario"])
    print(hr)
    print("  {:<35} {:>10} {:>10}".format("Metric", "Greedy", "CP-SAT"))
    print(hr)
    print("  {:<35} {:>10} {:>10}".format("Coverage rate", g_cov_s, c_cov_s))
    print("  {:<35} {:>10} {:>10}".format("Total shifts assigned", g["total_shifts"], c_tot_s))
    print("  {:<35} {:>10.2f} {:>10}".format("Workload sigma (shifts)", g["imbalance"]["std"], c_std_s))
    print("  {:<35} {:>10} {:>10}".format("Max shifts (any worker)", g["imbalance"]["max"], c_max_s))
    print("  {:<35} {:>10} {:>10}".format("Uncovered slots", g["uncovered_slots"], c_unc_s))
    print("  {:<35} {:>10} {:>10}".format("C4 violations (night->morning)", g["c4_violations"], c_c4_s))
    print("  {:<35} {:>10} {:>9.0f}".format("Solver time (ms)", "<1", c["wall_time_s"] * 1000))
    print(hr)
    if imp["shift_reduction_pct"] is not None and imp["imbalance_reduction_pct"] is not None:
        print("  >> Shift reduction: {:+.1f}%  |  Imbalance reduction: {:+.1f}%".format(
            imp["shift_reduction_pct"], imp["imbalance_reduction_pct"]))
    print()
