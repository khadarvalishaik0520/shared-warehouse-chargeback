"""Exploratory: accuracy of permutation-sampled Shapley when AUTO_SUSPEND < 60 s (resume minimum binds), vs exact."""
import random, sys, statistics as st
from itertools import combinations
import os
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "chargeback")]
from common.billing import periods, billed_seconds, shapley_bruteforce, shapley_sweep
from engine import r5_shapley
rng = random.Random(11); res = {k: [] for k in (100, 500, 2000, 5000)}; sweep_err = []; core = {"exact": 0, 2000: 0, "sweep": 0}; checks = 0
inst_core = {"exact": 0, 2000: 0, "sweep": 0}; N = 300
for trial in range(N):
    n = rng.randint(4, 8); a = rng.choice([0, 30])
    T = {"t%d" % i: [(s, s + rng.expovariate(1 / 8)) for s in (rng.uniform(0, 3600) for _ in range(rng.randint(1, 12)))] for i in range(n)}
    P = {t: periods(v, a) for t, v in T.items()}
    bill = billed_seconds([x for v in T.values() for x in v], a)
    ex = shapley_bruteforce(T, a)
    for k in res:
        ph, _ = r5_shapley(T, P, a, samples=k, seed=trial)
        res[k].append(100 * max(abs(ph[t] - ex[t]) for t in T) / bill)
        if k == 2000: samp = ph
    sw = shapley_sweep(T, a); sw = {t: v * bill / sum(sw.values()) for t, v in sw.items()}  # sweep rescaled to the bill
    sweep_err.append(100 * max(abs(sw[t] - ex[t]) for t in T) / bill)
    viol = {"exact": False, 2000: False, "sweep": False}
    for kk in range(1, n):
        for S in combinations(T, kk):
            checks += 1; c = billed_seconds([x for t in S for x in T[t]], a)
            for name, phi in (("exact", ex), (2000, samp), ("sweep", sw)):
                if sum(phi[t] for t in S) > c + 1e-6: core[name] += 1; viol[name] = True
    for k2 in viol: inst_core[k2] += viol[k2]
for k, v in res.items():
    print("samples %5d: max per-team error, %% of bill: median %.2f p95 %.2f max %.2f" % (k, st.median(v), sorted(v)[int(.95 * len(v))], max(v)))
print("rescaled sweep: median %.2f p95 %.2f max %.2f" % (st.median(sweep_err), sorted(sweep_err)[int(.95 * len(sweep_err))], max(sweep_err)))
print("coalitions checked %d; violations exact %d, sampled-2000 %d, sweep %d; instances with any: exact %d, sampled %d, sweep %d of %d"
      % (checks, core["exact"], core[2000], core["sweep"], inst_core["exact"], inst_core[2000], inst_core["sweep"], N))
