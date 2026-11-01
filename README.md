# Planning and Scheduling Optimisation — OR-Tools CP-SAT

[![tests](https://github.com/ViswanathDas/planning-scheduling-opt/actions/workflows/tests.yml/badge.svg)](https://github.com/ViswanathDas/planning-scheduling-opt/actions/workflows/tests.yml)

Workforce shift scheduling solved with Google OR-Tools CP-SAT.
Compares a **greedy heuristic baseline** against a **constraint-programming solver**
across three generated stress scenarios.

---

## Problem

Assign workers to shifts over a planning horizon to meet operational requirements.

**Hard constraints (five):**
- **C1** Minimum coverage: each shift slot must have >= N workers
- **C2** Maximum coverage: each shift slot has <= N_max workers
- **C3** Worker availability: workers can only be assigned to available slots
- **C4** Rest requirement: no worker assigned to a night shift and a morning shift on the following day
- **C5** Maximum shifts in every rolling 7-day window (an earlier version checked fixed calendar weeks only; fixed in Nov 2026, results unchanged)

**Objective (minimise):**
```
5 * total_shifts  +  10 * (max_assigned - min_assigned)  -  preference_score
```
- Efficiency: minimise total shifts assigned (avoid overstaffing)
- Fairness: minimise workload imbalance across workers
- Preference: maximise worker preference satisfaction (soft)

---

## Results

Three scenarios were generated with fixed random seeds (reproducible; run `python notebooks/run_comparison.py` or `pytest tests/`):

| Scenario | Workers | Days | Unavailability | Greedy C4 violations | CP-SAT C4 violations | Workload sigma (greedy) | Workload sigma (CP-SAT) | CP-SAT status and time |
|----------|---------|------|----------------|---------------------|---------------------|------------------------|------------------------|------------|
| A — Baseline | 12 | 7 | 20% | 3 | **0** | 0.28 | 0.28 | optimal, about 23 s |
| B — Tight availability | 12 | 7 | 40% | 3 | **0** | 0.49 | 0.76 | optimal, about 0.4 s |
| C — Hard / Scaled | 20 | 14 | 30% | 8 | **0** | 0.32 | **0.00** | optimal, about 0.4 s |

Solve times are wall-clock on a laptop with 4 search workers and vary by machine.

Key findings:
- **CP-SAT eliminates all C4 (rest) violations** across every scenario. The greedy heuristic has no temporal lookahead and cannot enforce this constraint.
- **Scenario C: perfect workload balance.** CP-SAT assigns every worker exactly 7 shifts (sigma 0.00), against 0.32 for greedy.
- **Scenario B: balance gets worse, and that is the honest trade-off.** With 40 percent unavailability, removing the rest violations forces some workers onto fewer shifts. The objective balances only max minus min shifts and also rewards preferences, so sigma rises from 0.49 to 0.76 while every hard constraint holds.
- **Scenario A is the slowest to prove optimal** despite being the smallest, because many workers are interchangeable and the solver spends its time on symmetric alternatives. Symmetry breaking is the obvious next improvement.
- **Greedy is fast and coverage-complete** but cannot enforce cross-day rest constraints or achieve global workload balance

---

## Project Structure

```
planning-scheduling-opt/
├── src/
│   ├── data_generator.py   # Scenario generation (3 presets, seeded RNG)
│   ├── model.py            # OR-Tools CP-SAT model (5 constraints, weighted objective)
│   ├── greedy.py           # Coverage-first greedy baseline
│   ├── metrics.py          # Evaluation: coverage rate, imbalance, C4 violations
│   └── visualise.py        # 4 comparison plots
├── notebooks/
│   └── run_comparison.py   # Main entry point
├── results/                # Generated plots (PNG)
└── requirements.txt
```

---

## Scenarios

Generated via `data_generator.py` — no external data required.

**Scenario A — Baseline** (seed=42)
- 12 workers (4 senior, 8 junior), 7 days, ~20% unavailability
- Coverage: morning≥3, afternoon≥2, night≥2

**Scenario B — Tight Availability** (seed=7)
- Same size, ~40% unavailability — stresses availability constraint
- Soft coverage mode: shortfall penalised in objective to guarantee feasibility

**Scenario C — Hard / Scaled** (seed=99)
- 20 workers, 14 days, ~30% unavailability, higher coverage requirements (morning≥4)
- Demonstrates solver scaling and fairness optimisation

---

## Usage

```bash
pip install -r requirements.txt
python notebooks/run_comparison.py
```

Plots saved to `results/`:
- `plot1_heatmap_[a/b/c].png` — side-by-side schedule heatmaps
- `plot2_utilisation_[a/b/c].png` — per-worker shifts (greedy vs CP-SAT)
- `plot3_coverage_[a/b/c].png` — slot-level coverage vs minimum required
- `plot4_summary.png` — cross-scenario comparison (total shifts, coverage, imbalance, solve time)

---

## Why CP-SAT over LP?

Constraint C4 (no night-then-morning) is a logical implication between binary variables
across time steps. This is naturally expressed as a CP constraint:
```python
model.Add(x[(w, d, NIGHT)] + x[(w, d+1, MORNING)] <= 1)
```
An LP relaxation would need big-M integer formulation — less clean and slower for
small combinatorial problems. CP-SAT handles this natively through propagation.

The fairness objective (`AddMaxEquality` / `AddMinEquality`) similarly has no clean LP
equivalent without auxiliary variables and linearisation tricks.

---

## Technical Stack

- **Python 3.10+**
- **OR-Tools** (CP-SAT solver)
- **NumPy / matplotlib** (analysis and visualisation)
- No external datasets — all scenarios self-generated

## Tests

```bash
pip install pytest
pytest tests/ -q
```

The tests check every hard constraint on the CP-SAT schedules (coverage bounds, availability, night-then-morning rest, rolling weekly cap), that the solver proves optimality, and the scenario C headline numbers.
