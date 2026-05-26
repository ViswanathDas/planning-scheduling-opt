"""
run_comparison.py
-----------------
Main entry point. Runs all three scenarios end-to-end:
    1. Generate scenario dataset
    2. Run greedy baseline
    3. Run CP-SAT solver
    4. Print comparison table
    5. Save all four plots to results/

Usage:
    cd planning-scheduling-opt
    python notebooks/run_comparison.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.data_generator import generate_scenario, print_scenario_summary, SCENARIO_CONFIGS
from src.greedy import schedule_greedy, print_greedy_summary
from src.model import solve, print_result_summary
from src.metrics import compare, print_comparison_table
from src.visualise import (
    plot_heatmap, plot_utilisation, plot_coverage, plot_solve_metrics
)

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")


def run_scenario(key: str) -> dict:
    scenario = generate_scenario(key)
    print_scenario_summary(scenario)

    print("\n  Running greedy baseline...")
    greedy = schedule_greedy(scenario)
    print_greedy_summary(scenario, greedy)

    print("\n  Running CP-SAT solver...")
    # Scenario B has tight availability — use soft coverage to guarantee a solution
    soft = (key == "B")
    cpsat = solve(scenario, time_limit_s=30.0, soft_coverage=soft)
    print_result_summary(scenario, cpsat)

    comp = compare(scenario, greedy, cpsat)
    print_comparison_table(comp)

    label = key.lower()

    print(f"\n  Generating plots for Scenario {key}...")
    plot_heatmap(
        scenario, greedy, cpsat,
        os.path.join(RESULTS_DIR, f"plot1_heatmap_{label}.png")
    )
    plot_utilisation(
        scenario, greedy, cpsat,
        os.path.join(RESULTS_DIR, f"plot2_utilisation_{label}.png")
    )
    plot_coverage(
        scenario, greedy, cpsat,
        os.path.join(RESULTS_DIR, f"plot3_coverage_{label}.png")
    )

    return comp


def main():
    print("\n" + "=" * 62)
    print("  PLANNING & SCHEDULING OPTIMISATION — OR-Tools CP-SAT")
    print("=" * 62)

    os.makedirs(RESULTS_DIR, exist_ok=True)

    comparisons = []
    for key in ["A", "B", "C"]:
        comp = run_scenario(key)
        comparisons.append(comp)

    # Summary plot across all scenarios
    print("\n  Generating summary plot...")
    plot_solve_metrics(
        comparisons,
        os.path.join(RESULTS_DIR, "plot4_summary.png")
    )

    # Final results table
    print("\n" + "=" * 62)
    print("  OVERALL RESULTS SUMMARY")
    print("=" * 62)

    for comp in comparisons:
        imp = comp["improvement"]
        g   = comp["greedy"]
        c   = comp["cpsat"]
        sr  = f"{imp['shift_reduction_pct']:+.1f}%" if imp["shift_reduction_pct"] else "n/a"
        ir  = f"{imp['imbalance_reduction_pct']:+.1f}%" if imp["imbalance_reduction_pct"] else "n/a"
        print(f"\n  {comp['scenario']}")
        print(f"    Greedy coverage:  {g['coverage_rate']*100:.1f}%  "
              f"  CP-SAT coverage: "
              f"{c['coverage_rate']*100:.1f}%" if c['coverage_rate'] else "  CP-SAT: INFEASIBLE")
        print(f"    Shift reduction:  {sr}  |  Imbalance reduction: {ir}")
        print(f"    C4 violations (greedy): {g['c4_violations']}  |  "
              f"CP-SAT solver: {c['solver_status']}  "
              f"({c['wall_time_s']*1000:.0f}ms)")

    print(f"\n  All plots saved to: {os.path.abspath(RESULTS_DIR)}/")
    print("\nDone.\n")


if __name__ == "__main__":
    main()
