"""Chargeback engine: splits one shared warehouse's bill across teams with five rules (pre-registered R1–R5).
Input: dict team -> list of (start, end) epoch seconds (one instance, one billing month), auto-suspend seconds.
All rules except R1 sum exactly to the modeled bill. Works for any auto; R5's sweep is exact only when auto >= 60
(Theorem 1, PROOF_NOTES.md); for auto < 60 R5 falls back to permutation sampling (marked approximate)."""
import os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common.billing import billed_seconds, periods, shapley_sweep, MIN_BILL


def exec_seconds(v):
    return sum(e - s for s, e in v)


def r1_execution_only(T, auto):
    """Native-style attribution: each second with queries running is split equally among the queries running in it
    (native attribution weights by resource use, which traces do not record). Idle time, tails and resume minimums stay
    unassigned. Deviation 1 (2026-10-20): the first run summed raw execution seconds, which double-counts concurrency."""
    ev = []
    for t, v in T.items():
        for s, e in v:
            if e > s: ev.append((s, 1, t)); ev.append((e, -1, t))
    ev.sort(key=lambda x: (x[0], x[1]))
    out = {t: 0.0 for t in T}; cnt = {}; n = 0; prev = None
    for x, d, t in ev:
        if prev is not None and n > 0 and x > prev:
            w = (x - prev) / n
            for a, k in cnt.items(): out[a] += w * k
        cnt[t] = cnt.get(t, 0) + d
        if cnt[t] == 0: del cnt[t]
        n += d; prev = x
    return out


def r2_proportional(T, auto, bill):
    x = r1_execution_only(T, auto); z = sum(x.values()) or 1.0
    return {t: bill * x[t] / z for t in T}


def r3_equal(T, auto, bill):
    return {t: bill / len(T) for t in T}


def coalition_cost(P, S):
    """Billed seconds of coalition S from each team's own running periods P[t] (exact by Lemma 1)."""
    iv = sorted(x for t in S for x in P[t])
    if not iv: return 0.0
    tot = 0.0; s0, e0 = iv[0]
    for s, e in iv[1:]:
        if s <= e0: e0 = max(e0, e)
        else: tot += max(MIN_BILL, e0 - s0); s0, e0 = s, e
    return tot + max(MIN_BILL, e0 - s0)


def r4_marginal(P, bill):
    """Leave-one-out marginal cost c(N) - c(N\\{i}), rescaled to sum to the bill."""
    m = {t: bill - coalition_cost(P, [u for u in P if u != t]) for t in P}
    z = sum(m.values())
    return {t: (bill * m[t] / z if z > 0 else bill / len(P)) for t in P}


def r5_shapley(T, P, auto, samples=2000, seed=0):
    if auto >= MIN_BILL:
        return shapley_sweep(T, auto), True
    rng = random.Random(seed); teams = list(P); phi = {t: 0.0 for t in teams}
    for _ in range(samples):          # permutation sampling (approximate); used only when the resume minimum can bind
        rng.shuffle(teams); acc = []; prev = 0.0
        for t in teams:
            acc.append(t); c = coalition_cost(P, acc); phi[t] += c - prev; prev = c
    return {t: v / samples for t, v in phi.items()}, False


def allocate(T, auto):
    """Returns bill, unassigned share under R1, and each rule's charges."""
    T = {t: v for t, v in T.items() if v}
    P = {t: periods(v, auto) for t, v in T.items()}
    bill = coalition_cost(P, list(P))
    r1 = r1_execution_only(T, auto)
    r5, exact = r5_shapley(T, P, auto)
    return {"bill_s": bill, "unassigned_s": bill - sum(r1.values()), "r5_exact": exact, "P": P,
            "R1": r1, "R2": r2_proportional(T, auto, bill), "R3": r3_equal(T, auto, bill),
            "R4": r4_marginal(P, bill), "R5": r5}


def core_violations(T, alloc, auto, max_k=None):
    """Coalitions (all if <= 12 teams, else singletons and pairs) charged more than their standalone bill."""
    from itertools import combinations
    teams = list(T); n = len(teams); ks = range(1, n) if n <= 12 else (1, 2)
    viol = tot = 0
    for k in ks:
        for S in combinations(teams, k):
            tot += 1
            if sum(alloc[t] for t in S) > billed_seconds([x for t in S for x in T[t]], auto) + 1e-6: viol += 1
    return viol, tot
