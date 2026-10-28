"""E2 + E3 runner (pre-registered in PLAN.md). One row per (instance, calendar month, AUTO_SUSPEND).
Writes results/e2e3.jsonl; re-runnable (skips finished instance/auto pairs). Python 3.9 compatible.
Usage: python3 run_e2e3.py <redset_iv dir> <results dir> [max_instances] [--no-compile]
--no-compile: the pre-registered sensitivity (frozen definitions) with compile time removed from each interval;
writes results/e2e3_nocompile.jsonl, main settings 60/300/600 s only."""
import sys, os, json, time, datetime, duckdb
from itertools import combinations
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, ".."))
from engine import allocate, coalition_cost

AUTOS = (60, 300, 600, 30)          # 30 s = resume minimum binds (reported separately)
SUBSET_ALL_MAX = 10                 # all coalitions when <= 10 teams, else singletons, pairs and complements

def coalitions(teams):
    n = len(teams)
    if n <= SUBSET_ALL_MAX:
        for k in range(1, n):
            for S in combinations(teams, k): yield S
    else:
        for t in teams: yield (t,); yield tuple(u for u in teams if u != t)
        for S in combinations(teams, 2): yield S

NC = "--no-compile" in sys.argv
E = "e - compile_s" if NC else "e"                       # interval end, with or without compile time
if NC: AUTOS = (60, 300, 600)

def main(d, res, cap):
    os.makedirs(res, exist_ok=True); outp = os.path.join(res, "e2e3_nocompile.jsonl" if NC else "e2e3.jsonl")
    done = set()
    if os.path.exists(outp):
        for l in open(outp): r = json.loads(l); done.add((r["key"], r["auto"]))
    elig = [json.loads(l) for l in open(os.path.join(d, "eligibility.jsonl"))]
    elig = [r for r in elig if r["eligible"]][:cap]
    con = duckdb.connect(); out = open(outp, "a")
    for r in elig:
        f = os.path.join(d, r["key"].replace("/", "_") + ".parquet")
        sh = dict(con.execute(f"select team, sum({E} - s) from '{f}' group by team").fetchall())
        tot = sum(sh.values()) or 1.0
        keep = {t for t, x in sh.items() if x / tot >= 0.01}          # frozen rule: teams with >= 1% share
        months = [m for (m,) in con.execute(f"select distinct strftime(to_timestamp(s), '%Y-%m') m from '{f}' order by 1").fetchall()]
        bymonth = {}
        for m in months:
            T = {}
            for t, s, e in con.execute(f"select team, s, {E} from '{f}' where strftime(to_timestamp(s), '%Y-%m') = ? order by s", [m]).fetchall():
                T.setdefault(t if t in keep else "other", []).append((s, e))
            bymonth[m] = T
        for auto in AUTOS:
            if (r["key"], auto) in done: continue
            t0 = time.time()
            for m in months:
                T = bymonth[m]
                if len(T) < 2: continue
                a = allocate(T, auto); P = a["P"]
                teams = list(T); stand = {t: coalition_cost(P, (t,)) for t in teams}
                viol = {k: 0 for k in ("R2", "R3", "R4", "R5")}; ncoal = 0
                for S in coalitions(teams):
                    ncoal += 1; c = coalition_cost(P, S)
                    for k in viol:
                        if sum(a[k][t] for t in S) > c + 1e-6: viol[k] += 1
                rec = {"key": r["key"], "kind": r["kind"], "month": m, "auto": auto, "teams": len(teams),
                       "bill_s": a["bill_s"], "unassigned_s": a["unassigned_s"], "r5_exact": a["r5_exact"],
                       "standalone_s": {str(t): stand[t] for t in teams},
                       "exec_s": {str(t): a["R1"][t] for t in teams},
                       "charges": {k: {str(t): a[k][t] for t in teams} for k in ("R2", "R3", "R4", "R5")},
                       "core_viol": viol, "coalitions_checked": ncoal}
                out.write(json.dumps(rec) + "\n"); out.flush()
            print(r["key"], "auto", auto, "months", len(months), "%.0fs" % (time.time() - t0), flush=True)
    print("E2E3 DONE")

if __name__ == "__main__":
    av = [x for x in sys.argv[1:] if not x.startswith("--")]
    main(av[0], av[1], int(av[2]) if len(av) > 2 else 10**9)
