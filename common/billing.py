"""Billing core shared by both papers (code only; the two papers share no experiments or results).

Model of a per-second-billed warehouse at a fixed size (Snowflake-style rules):
  * the warehouse resumes when a query arrives while it is suspended;
  * it stays running while queries run and for AUTO_SUSPEND seconds after the last one ends;
  * each running period is billed per second with a minimum of MIN_BILL seconds.
Intervals are (start, end) in epoch seconds of query execution on that warehouse.
"""
from itertools import combinations
from math import factorial

MIN_BILL = 60.0


def periods(intervals, auto):
    """Merge query intervals into running periods [resume, suspend)."""
    if not intervals:
        return []
    iv = sorted(intervals)
    out = []
    s0, e0 = iv[0]
    for s, e in iv[1:]:
        if s <= e0 + auto:
            e0 = max(e0, e)
        else:
            out.append((s0, e0 + auto))
            s0, e0 = s, e
    out.append((s0, e0 + auto))
    return out


def billed_seconds(intervals, auto, min_bill=MIN_BILL):
    """Billed seconds = sum over running periods of max(min_bill, length)."""
    return sum(max(min_bill, e - s) for s, e in periods(intervals, auto))


def busy_seconds(intervals):
    """Seconds with at least one query executing (union of intervals)."""
    return sum(e - s for s, e in periods(intervals, 0.0))


# ---------------------------------------------------------------- allocation rules (paper 2 uses these)
def proportional(team_intervals, auto, min_bill=MIN_BILL):
    """Split the full bill by each team's share of execution seconds (common FinOps practice)."""
    total = billed_seconds([x for v in team_intervals.values() for x in v], auto, min_bill)
    exe = {t: sum(e - s for s, e in v) for t, v in team_intervals.items()}
    z = sum(exe.values()) or 1.0
    return {t: total * exe[t] / z for t in team_intervals}


def shapley_bruteforce(team_intervals, auto, min_bill=MIN_BILL):
    """Exact Shapley value of the coalition-cost game c(S)=billed(union of S's queries). Exponential; tests only."""
    teams = list(team_intervals)
    n = len(teams)
    cache = {}

    def c(S):
        key = frozenset(S)
        if key not in cache:
            cache[key] = billed_seconds([x for t in S for x in team_intervals[t]], auto, min_bill) if S else 0.0
        return cache[key]

    phi = {}
    for i in teams:
        others = [t for t in teams if t != i]
        v = 0.0
        for k in range(n):
            w = factorial(k) * factorial(n - k - 1) / factorial(n)
            for S in combinations(others, k):
                v += w * (c(S + (i,)) - c(S))
        phi[i] = v
    return phi


def shapley_sweep(team_intervals, auto):
    """Exact Shapley in O(m log m) when the resume minimum never binds (auto >= MIN_BILL):
    then billed(S) is the measure of the union of [start, end+auto] over S's queries (a coverage game),
    and each team's Shapley charge is the sum, over billed time, of 1/(number of teams covering that instant)."""
    ev = []
    for t, v in team_intervals.items():
        for s, e in periods(v, auto):          # team's own extended coverage, already merged
            ev.append((s, 1, t))
            ev.append((e, -1, t))
    ev.sort(key=lambda x: (x[0], x[1]))
    phi = {t: 0.0 for t in team_intervals}
    active = {}
    prev = None
    for x, d, t in ev:
        if prev is not None and active and x > prev:
            share = (x - prev) / len(active)
            for a in active:
                phi[a] += share
        if d == 1:
            active[t] = active.get(t, 0) + 1
        else:
            active[t] -= 1
            if active[t] == 0:
                del active[t]
        prev = x
    return phi
