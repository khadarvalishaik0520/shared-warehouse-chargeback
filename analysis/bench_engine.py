"""Timing benchmark: synthetic one-month warehouse, 10 teams, 1M queries."""
import random, time, sys
import os
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "chargeback")]
from common.billing import shapley_sweep
from engine import allocate
rng = random.Random(1); M = 30 * 86400; T = {}
for i in range(10):
    v = []
    for _ in range(100_000):
        s = rng.uniform(0, M); v.append((s, s + rng.expovariate(1 / 5)))
    T["t%d" % i] = sorted(v)
for auto in (60, 600):
    t0 = time.perf_counter(); shapley_sweep(T, auto); t1 = time.perf_counter(); allocate(T, auto); t2 = time.perf_counter()
    print("auto %d: sweep %.2fs, all rules %.2fs" % (auto, t1 - t0, t2 - t1))
