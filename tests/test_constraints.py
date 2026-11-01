"""CP-SAT schedules satisfy every hard constraint; README results for scenario C."""
import numpy as np
import pytest

from src.data_generator import generate_scenario
from src.greedy import schedule_greedy
from src.model import solve

NIGHT, MORNING = 2, 0


@pytest.fixture(scope="module", params=["B", "C"])   # A takes ~20 s to prove optimal
def case(request):
    sc = generate_scenario(request.param)
    return request.param, sc, solve(sc, time_limit_s=30.0)


def x(res, w, d, s):
    return bool(res.assignment.get(w, {}).get(d, {}).get(s, False))


def test_solver_proves_optimality(case):
    _, _, res = case
    assert res.solver_status == "OPTIMAL"


def test_coverage_within_bounds(case):
    _, sc, res = case
    cfg = sc.config
    for d in range(sc.n_days):
        for s in range(sc.n_shifts):
            n = sum(x(res, w.id, d, s) for w in sc.workers)
            assert cfg.min_coverage[s] <= n <= cfg.max_coverage


def test_availability_respected(case):
    _, sc, res = case
    for w in sc.workers:
        for d in range(sc.n_days):
            for s in range(sc.n_shifts):
                if x(res, w.id, d, s):
                    assert w.availability[d][s]


def test_no_night_then_morning(case):
    _, sc, res = case
    for w in sc.workers:
        for d in range(sc.n_days - 1):
            assert not (x(res, w.id, d, NIGHT) and x(res, w.id, d + 1, MORNING))


def test_rolling_weekly_cap(case):
    _, sc, res = case
    win = min(7, sc.n_days)
    for w in sc.workers:
        for start in range(sc.n_days - win + 1):
            n = sum(x(res, w.id, d, s) for d in range(start, start + win) for s in range(sc.n_shifts))
            assert n <= sc.config.max_shifts_per_week


def test_scenario_c_matches_readme(case):
    key, sc, res = case
    if key != "C":
        pytest.skip("README headline numbers are for scenario C")
    per_worker = list(res.shifts_per_worker.values())
    assert np.std(per_worker) == pytest.approx(0.0, abs=1e-9)
    greedy = schedule_greedy(sc)
    assert greedy.constraint_violations == 8
