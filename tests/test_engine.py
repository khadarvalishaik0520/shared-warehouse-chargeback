import sys, os, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "chargeback"))
from engine import allocate, core_violations
from common.billing import shapley_bruteforce
rng = random.Random(3)
def inst(n=4):
    return {"t%d" % i: [(s, s + rng.expovariate(1/30)) for s in (rng.uniform(0, 3600) for _ in range(rng.randint(1, 8)))] for i in range(n)}
for auto in (60, 300, 600, 30):
    for _ in range(50):
        T = inst(rng.randint(2, 5)); a = allocate(T, auto)
        for r in ("R2", "R3", "R4", "R5"):
            assert abs(sum(a[r].values()) - a["bill_s"]) < (1e-6 if r != "R5" or a["r5_exact"] else a["bill_s"] * 0.05), (r, auto)
        if auto >= 60:
            assert core_violations(T, a["R5"], auto)[0] == 0
        else:   # sampled Shapley close to exact
            ex = shapley_bruteforce(T, auto)
            assert max(abs(ex[t] - a["R5"][t]) for t in T) < 0.05 * a["bill_s"] + 5
from engine import r1_execution_only
from common.billing import busy_seconds
for _ in range(200):          # R1 never exceeds busy time, and equals it exactly
    T = inst(rng.randint(2, 5)); r1 = r1_execution_only(T, 60)
    assert abs(sum(r1.values()) - busy_seconds([x for v in T.values() for x in v])) < 1e-6
r = r1_execution_only({"a": [(0, 10)], "b": [(0, 10)], "c": [(5, 10)]}, 60)
assert abs(r["a"] - (2.5 + 5 / 3)) < 1e-9 and abs(r["c"] - 5 / 3) < 1e-9
print("ENGINE TESTS PASSED")
