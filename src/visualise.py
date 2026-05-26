"""
visualise.py
------------
Four comparison plots for greedy vs CP-SAT scheduling results.

Plot 1 — Schedule Heatmap (side-by-side)
Plot 2 — Worker Utilisation Bar Chart
Plot 3 — Coverage vs Requirement per Slot
Plot 4 — Solve Metrics vs Scenario (time + objective)
"""

from __future__ import annotations
import os
from typing import Dict, List

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from src.data_generator import Scenario, SHIFT_NAMES
from src.greedy import GreedyResult
from src.model import ScheduleResult

# ── Colour palette ────────────────────────────────────────────────────────────
C_CPSAT    = "#2E75B6"   # deep blue
C_GREEDY   = "#E8751A"   # orange
C_AVAIL    = "#FFFFFF"   # white  (available, not assigned)
C_UNAVAIL  = "#CCCCCC"   # grey   (unavailable)
C_ASSIGNED = C_CPSAT
C_GREEDY_A = C_GREEDY


def _save(fig, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


# ── Plot 1: Schedule Heatmap ──────────────────────────────────────────────────

def plot_heatmap(scenario: Scenario,
                 greedy: GreedyResult,
                 cpsat: ScheduleResult,
                 save_path: str) -> None:
    """
    Side-by-side heatmaps: workers (rows) × (day × shift) columns.
    Green = assigned, grey = unavailable, white = available but not assigned.
    """
    cfg = scenario.config
    W, D, S = cfg.n_workers, cfg.n_days, cfg.n_shifts
    cols = D * S  # total slot columns

    # Build colour matrices
    def build_matrix(assignment, availability):
        mat = np.zeros((W, cols), dtype=float)
        for w in range(W):
            for d in range(D):
                for s in range(S):
                    col = d * S + s
                    if assignment[w][d][s]:
                        mat[w, col] = 1.0     # assigned
                    elif not availability[w][d][s]:
                        mat[w, col] = 0.5     # unavailable
                    else:
                        mat[w, col] = 0.0     # available, not assigned
        return mat

    avail = {w: scenario.workers[w].availability for w in range(W)}

    g_mat = build_matrix(greedy.assignment, avail)
    c_mat = build_matrix(cpsat.assignment if cpsat.feasible else
                         {w: {d: {s: False for s in range(S)} for d in range(D)}
                          for w in range(W)}, avail)

    fig, axes = plt.subplots(1, 2, figsize=(max(14, cols * 0.35), max(5, W * 0.35)),
                             sharey=True)
    fig.suptitle(f"Schedule Heatmap — {cfg.name}", fontsize=12, fontweight="bold", y=1.02)

    cmap = matplotlib.colors.ListedColormap([C_AVAIL, C_UNAVAIL, C_GREEDY_A])
    cmap2 = matplotlib.colors.ListedColormap([C_AVAIL, C_UNAVAIL, C_ASSIGNED])
    bounds = [0, 0.25, 0.75, 1.05]
    norm   = matplotlib.colors.BoundaryNorm(bounds, cmap.N)

    for ax, mat, title, cm in [(axes[0], g_mat, "Greedy", cmap),
                                (axes[1], c_mat, "CP-SAT", cmap2)]:
        ax.imshow(mat, aspect="auto", cmap=cm, norm=norm,
                  interpolation="nearest")
        ax.set_title(title, fontsize=11)
        ax.set_xlabel("Day × Shift slot")
        ax.set_yticks(range(W))
        ax.set_yticklabels([scenario.workers[w].name for w in range(W)],
                           fontsize=7)

        # Day boundaries
        for d in range(1, D):
            ax.axvline(d * S - 0.5, color="#888888", linewidth=0.5, linestyle="--")

        # Shift labels on x-axis (every day)
        xtick_pos = [d * S + s for d in range(D) for s in range(S)]
        xtick_lab = [SHIFT_NAMES[s][0] for d in range(D) for s in range(S)]  # M/A/N
        ax.set_xticks(xtick_pos)
        ax.set_xticklabels(xtick_lab, fontsize=6)

    # Legend
    handles = [
        mpatches.Patch(color=C_GREEDY_A, label="Assigned (Greedy)"),
        mpatches.Patch(color=C_ASSIGNED, label="Assigned (CP-SAT)"),
        mpatches.Patch(color=C_UNAVAIL,  label="Unavailable"),
        mpatches.Patch(color=C_AVAIL,    label="Available, not assigned"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=4, fontsize=8,
               bbox_to_anchor=(0.5, -0.04))

    axes[0].set_ylabel("Worker")
    plt.tight_layout()
    _save(fig, save_path)


# ── Plot 2: Worker Utilisation Bar Chart ──────────────────────────────────────

def plot_utilisation(scenario: Scenario,
                     greedy: GreedyResult,
                     cpsat: ScheduleResult,
                     save_path: str) -> None:
    """
    Grouped bar chart: shifts assigned per worker, Greedy vs CP-SAT.
    """
    cfg = scenario.config
    W   = cfg.n_workers
    x   = np.arange(W)
    width = 0.38

    g_vals = [greedy.shifts_per_worker[w] for w in range(W)]
    c_vals = [cpsat.shifts_per_worker.get(w, 0) for w in range(W)]

    fig, ax = plt.subplots(figsize=(max(10, W * 0.65), 5))

    bars_g = ax.bar(x - width/2, g_vals, width, label="Greedy",
                    color=C_GREEDY, alpha=0.85, edgecolor="white")
    if cpsat.feasible:
        bars_c = ax.bar(x + width/2, c_vals, width, label="CP-SAT",
                        color=C_CPSAT, alpha=0.85, edgecolor="white")

    ax.axhline(cfg.max_shifts_per_week, color="red", linestyle="--",
               linewidth=1, label=f"Max shifts/week ({cfg.max_shifts_per_week})")
    ax.axhline(sum(g_vals) / W, color=C_GREEDY, linestyle=":",
               linewidth=1, alpha=0.7, label="Greedy mean")
    if cpsat.feasible:
        ax.axhline(sum(c_vals) / W, color=C_CPSAT, linestyle=":",
                   linewidth=1, alpha=0.7, label="CP-SAT mean")

    ax.set_title(f"Worker Utilisation — {cfg.name}", fontsize=11, fontweight="bold")
    ax.set_xlabel("Worker")
    ax.set_ylabel("Shifts assigned")
    ax.set_xticks(x)
    ax.set_xticklabels([scenario.workers[w].name for w in range(W)],
                       rotation=45, ha="right", fontsize=7)
    ax.legend(fontsize=8)
    ax.set_ylim(0, cfg.max_shifts_per_week + 2)
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    _save(fig, save_path)


# ── Plot 3: Coverage vs Requirement per Slot ──────────────────────────────────

def plot_coverage(scenario: Scenario,
                  greedy: GreedyResult,
                  cpsat: ScheduleResult,
                  save_path: str) -> None:
    """
    Per-slot coverage: actual workers assigned vs minimum required.
    Shows where greedy falls short and CP-SAT holds coverage.
    """
    cfg  = scenario.config
    D, S = cfg.n_days, cfg.n_shifts
    slots = [(d, s) for d in range(D) for s in range(S)]
    xs    = np.arange(len(slots))

    req_vals = [cfg.min_coverage[s] for (d, s) in slots]
    g_vals   = [greedy.coverage.get((d, s), 0) for (d, s) in slots]
    c_vals   = [cpsat.coverage.get((d, s), 0) if cpsat.feasible else 0
                for (d, s) in slots]

    fig, ax = plt.subplots(figsize=(max(14, len(slots) * 0.35), 5))

    ax.fill_between(xs, req_vals, alpha=0.1, color="red", label="Min required")
    ax.plot(xs, req_vals, color="red",    linewidth=1.5, linestyle="--",
            label="Minimum required")
    ax.plot(xs, g_vals,   color=C_GREEDY, linewidth=1.5, marker="o",
            markersize=3, label="Greedy", alpha=0.9)
    if cpsat.feasible:
        ax.plot(xs, c_vals, color=C_CPSAT, linewidth=1.5, marker="s",
                markersize=3, label="CP-SAT", alpha=0.9)

    # Mark under-covered greedy slots
    for i, (d, s) in enumerate(slots):
        if g_vals[i] < req_vals[i]:
            ax.axvspan(i - 0.4, i + 0.4, color="red", alpha=0.12)

    ax.set_title(f"Coverage vs Requirement per Slot — {cfg.name}",
                 fontsize=11, fontweight="bold")
    ax.set_xlabel(f"Slot index  (M=Morning, A=Afternoon, N=Night, repeating {D} days)")
    ax.set_ylabel("Workers assigned")

    # x-tick labels: M/A/N pattern
    labels = [SHIFT_NAMES[s][0] if d % 2 == 0 else "" for (d, s) in slots]
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, fontsize=6)

    # Day boundaries
    for d in range(1, D):
        ax.axvline(d * S - 0.5, color="#888888", linewidth=0.5, linestyle=":")

    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    ax.set_ylim(0, cfg.max_coverage + 1)

    plt.tight_layout()
    _save(fig, save_path)


# ── Plot 4: Solve Metrics vs Scenario ────────────────────────────────────────

def plot_solve_metrics(comparisons: List[Dict], save_path: str) -> None:
    """
    Summary plot across all scenarios:
    Left axis:  CP-SAT solve time (ms)
    Right axis: total shifts — Greedy vs CP-SAT
    """
    labels = [c["scenario"].split(" — ")[0] for c in comparisons]
    times  = [c["cpsat"]["wall_time_s"] * 1000 for c in comparisons]
    g_tot  = [c["greedy"]["total_shifts"] for c in comparisons]
    c_tot  = [c["cpsat"]["total_shifts"] if c["cpsat"]["total_shifts"] else 0
              for c in comparisons]
    g_cov  = [c["greedy"]["coverage_rate"] * 100 for c in comparisons]
    c_cov  = [(c["cpsat"]["coverage_rate"] * 100 if c["cpsat"]["coverage_rate"] else 0)
              for c in comparisons]
    g_std  = [c["greedy"]["imbalance"]["std"] for c in comparisons]
    c_std  = [(c["cpsat"]["imbalance"]["std"] if c["cpsat"]["imbalance"] else 0)
              for c in comparisons]

    x     = np.arange(len(labels))
    width = 0.35

    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    fig.suptitle("Greedy vs CP-SAT — Scenario Comparison",
                 fontsize=12, fontweight="bold")

    # --- Subplot 1: Total shifts
    ax = axes[0]
    ax.bar(x - width/2, g_tot, width, color=C_GREEDY, alpha=0.85, label="Greedy")
    ax.bar(x + width/2, c_tot, width, color=C_CPSAT,  alpha=0.85, label="CP-SAT")
    ax.set_title("Total shifts assigned", fontsize=10)
    ax.set_xticks(x); ax.set_xticklabels(labels)
    ax.set_ylabel("Shifts"); ax.legend(fontsize=8); ax.grid(axis="y", alpha=0.3)

    # --- Subplot 2: Coverage rate
    ax = axes[1]
    ax.bar(x - width/2, g_cov, width, color=C_GREEDY, alpha=0.85, label="Greedy")
    ax.bar(x + width/2, c_cov, width, color=C_CPSAT,  alpha=0.85, label="CP-SAT")
    ax.axhline(100, color="black", linestyle="--", linewidth=1, alpha=0.5)
    ax.set_title("Coverage rate (%)", fontsize=10)
    ax.set_xticks(x); ax.set_xticklabels(labels)
    ax.set_ylabel("%"); ax.set_ylim(0, 110); ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.3)

    # --- Subplot 3: Workload std + solve time
    ax = axes[2]
    ax2 = ax.twinx()
    ax.bar(x - width/2, g_std, width, color=C_GREEDY, alpha=0.85, label="Greedy σ")
    ax.bar(x + width/2, c_std, width, color=C_CPSAT,  alpha=0.85, label="CP-SAT σ")
    ax2.plot(x, times, color="black", marker="D", linewidth=1.5,
             markersize=5, label="Solve time (ms)")
    ax.set_title("Workload σ  +  Solve time", fontsize=10)
    ax.set_xticks(x); ax.set_xticklabels(labels)
    ax.set_ylabel("Workload σ (shifts)")
    ax2.set_ylabel("CP-SAT time (ms)")

    lines1, labs1 = ax.get_legend_handles_labels()
    lines2, labs2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labs1 + labs2, fontsize=7, loc="upper left")
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    _save(fig, save_path)
