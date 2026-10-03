"""Bootstrap: trek willekeurig hele avonden uit mijn live-sim trades en kijk hoe vaak ik de evaluatie haal."""
import random
import statistics

from .journal import group_days
from .personal import simulate_personal


def evenings_from_records(recs):
    """Alleen live-sim trades; alle trades van één avond blijven samen."""
    live = [t for t in recs if t["account"] == "live-sim"]
    return [trades for _, trades in group_days(live)]


def run_montecarlo(firm, rules, evenings, runs=10000, seed=1, max_days=120, consistency=None):
    if not evenings:
        return None
    rng = random.Random(seed)
    passed = failed = timeout = 0
    days_to_pass = []
    for _ in range(runs):
        days = ((d, d // 5, rng.choice(evenings)) for d in range(max_days))
        tr, _, n = simulate_personal(firm, rules, days, consistency)
        if tr.status == "PASS":
            passed += 1
            days_to_pass.append(n)
        elif tr.status == "FAIL":
            failed += 1
        else:
            timeout += 1
    return {
        "runs": runs,
        "pass_pct": 100.0 * passed / runs,
        "fail_pct": 100.0 * failed / runs,
        "timeout_pct": 100.0 * timeout / runs,
        "median_days_to_pass": statistics.median(days_to_pass) if days_to_pass else None,
    }
