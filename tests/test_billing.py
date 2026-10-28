import random, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common.billing import billed_seconds, shapley_bruteforce, shapley_sweep, proportional, periods
from itertools import combinations

def rand_inst(rng, teams=4, q=6, span=900):
    d = {}
    for i in range(teams):
        v = []
        for _ in range(rng.randint(1, q)):
            s = rng.uniform(0, span); v.append((s, s + rng.expovariate(1 / 20)))
        d["t%d" % i] = v
    return d

rng = random.Random(7)
# 1) hand case
assert billed_seconds([(0, 10)], 60) == 70
assert billed_seconds([(0, 1)], 0) == 60            # minimum binds
assert billed_seconds([(0, 10), (50, 60)], 60) == 120   # merged: 0..60+60
assert billed_seconds([(0, 10), (200, 210)], 60) == 140
# 2) sweep == brute-force Shapley whenever auto >= 60 (minimum cannot bind)
worst = 0.0
for trial in range(400):
    inst = rand_inst(rng, teams=rng.randint(2, 5))
    for auto in (60, 120, 300, 600):
        a = shapley_bruteforce(inst, auto); b = shapley_sweep(inst, auto)
        worst = max(worst, max(abs(a[t] - b[t]) for t in inst))
        total = billed_seconds([x for v in inst.values() for x in v], auto)
        assert abs(sum(b.values()) - total) < 1e-6          # efficiency: sums to the bill
print("sweep vs brute-force max abs diff (s):", worst)
assert worst < 1e-6
# 3) core check: no coalition pays more under Shapley than its standalone bill (auto >= 60)
viol = 0
for trial in range(300):
    inst = rand_inst(rng, teams=4)
    phi = shapley_sweep(inst, 300)
    for k in range(1, 4):
        for S in combinations(inst, k):
            if sum(phi[t] for t in S) > billed_seconds([x for t in S for x in inst[t]], 300) + 1e-6: viol += 1
print("Shapley core violations (auto=300):", viol)
assert viol == 0
# 4) where the minimum CAN bind (auto < 60), sweep is no longer exact: measure the gap
gap = 0.0
for trial in range(300):
    inst = rand_inst(rng, teams=4, q=3, span=3000)
    a = shapley_bruteforce(inst, 0); b = shapley_sweep(inst, 0)
    gap = max(gap, max(abs(a[t] - b[t]) for t in inst))
print("auto=0 (minimum binds): max sweep error (s):", round(gap, 2), "-> needs the min-bill extension")
# 5) proportional violates the core on some instances (illustration only, not a paper result)
pv = 0; tot = 0
for trial in range(300):
    inst = rand_inst(rng, teams=4)
    p = proportional(inst, 300)
    for t in inst:
        tot += 1
        if p[t] > billed_seconds(inst[t], 300) + 1e-6: pv += 1
print("proportional: teams charged above standalone bill: %d/%d" % (pv, tot))
print("ALL TESTS PASSED")
