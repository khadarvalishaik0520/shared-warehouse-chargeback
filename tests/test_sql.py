import duckdb, random, sys, time
import os
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)
from common.billing import shapley_sweep, billed_seconds, shapley_bruteforce
SQL = open(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "chargeback", "sql", "coverage_shapley.sql")).read()
rng = random.Random(5); worst = 0; wb = 0
for trial in range(500):
    T = {}
    for i in range(rng.randint(2, 6)):
        v = [(s, s + rng.expovariate(1 / 20)) for s in (rng.uniform(0, 5000) for _ in range(rng.randint(1, 15)))]
        if rng.random() < .3: v += [(v[0][0], v[0][1]), (v[0][0] + 1, v[0][0] + 1)]  # ties, zero-length
        T["t%d" % i] = v
    a = rng.choice([60, 120, 300, 600])
    con = duckdb.connect(); con.execute("create table queries(team varchar, s double, e double)")
    con.executemany("insert into queries values (?,?,?)", [(t, s, e) for t, v in T.items() for s, e in v])
    got = dict(con.execute(SQL, {"a": a}).fetchall()); ref = shapley_sweep(T, a)
    worst = max(worst, max(abs(got.get(t, 0) - ref[t]) for t in T))
    if len(T) <= 5 and trial < 100: bf = shapley_bruteforce(T, a); wb = max(wb, max(abs(got.get(t, 0) - bf[t]) for t in T))
    assert abs(sum(got.values()) - billed_seconds([x for v in T.values() for x in v], a)) < 1e-6
print("vs sweep max diff %.1e s; vs brute force %.1e s" % (worst, wb))
M = 30 * 86400
for n, a, dur in ((1_000_000, 60, "-5*ln(random())"), (1_000_000, 600, "-5*ln(random())"), (100_000, 60, "-5*ln(random())")):
    con = duckdb.connect()
    con.execute(f"create table queries as select 't' || (i % 10) as team, s, s + {dur} as e from (select i, random() * {M} as s from range({n}) t(i))")
    for thr in (1, 4):
        con.execute(f"set threads={thr}"); t0 = time.perf_counter(); con.execute(SQL, {"a": a}).fetchall()
        print("n=%d a=%d threads=%d: %.2f s" % (n, a, thr, time.perf_counter() - t0))
