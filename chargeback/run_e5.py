"""E5 runner (PLAN.md Addendum 4): one team adds 10 isolated one-second queries; do other teams' charges rise?
Usage: python3 run_e5.py <redset_iv dir> <results dir>"""
import sys, os, json, time, random, duckdb
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, ".."))
from engine import allocate
def main(d, res):
    os.makedirs(res, exist_ok=True); outp = os.path.join(res, "e5.jsonl")
    done = {(json.loads(l)["key"]) for l in open(outp)} if os.path.exists(outp) else set()
    elig = [json.loads(l) for l in open(os.path.join(d, "eligibility.jsonl"))]
    con = duckdb.connect(); out = open(outp, "a")
    for r in (x for x in elig if x["eligible"]):
        if r["key"] in done: continue
        t0 = time.time(); f = os.path.join(d, r["key"].replace("/", "_") + ".parquet")
        sh = dict(con.execute(f"select team, sum(e-s) from '{f}' group by team").fetchall()); tot = sum(sh.values()) or 1.0
        keep = {t for t, x in sh.items() if x / tot >= 0.01}
        months = [m for (m,) in con.execute(f"select distinct strftime(to_timestamp(s), '%Y-%m') from '{f}' order by 1").fetchall()]
        for m in months:
            T = {}
            for t, s, e in con.execute(f"select team, s, e from '{f}' where strftime(to_timestamp(s), '%Y-%m') = ? order by s", [m]).fetchall():
                T.setdefault(t if t in keep else "other", []).append((s, e))
            if len(T) < 2: continue
            lo = min(v[0][0] for v in T.values()); hi = max(e for v in T.values() for _, e in v)
            for auto in (60, 600):
                base = allocate(T, auto)
                for i in T:
                    if i == "other": continue
                    rng = random.Random("%s|%s|%s" % (r["key"], m, i))
                    add = [(x, x + 1.0) for x in (rng.uniform(lo, hi) for _ in range(10))]
                    T2 = dict(T); T2[i] = sorted(T[i] + add)
                    a = allocate(T2, auto)
                    rec = {"key": r["key"], "month": m, "auto": auto, "grower": str(i), "bill_before": base["bill_s"], "bill_after": a["bill_s"],
                           "others": {str(j): {k: [base[k][j], a[k][j]] for k in ("R2", "R4", "R5")} for j in T if j != i}}
                    out.write(json.dumps(rec) + "\n")
        out.flush(); print(r["key"], "months", len(months), "%.0fs" % (time.time() - t0), flush=True)
    print("E5 DONE")
if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
