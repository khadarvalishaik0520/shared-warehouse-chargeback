"""E7 runner (PLAN.md Addendum 5): standalone cost with each team's execution shortened by f, vs charges at full timing.
Usage: python3 run_e7.py <redset_iv dir> <results dir>"""
import sys, os, json, time, duckdb
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, ".."))
from engine import allocate
from common.billing import billed_seconds
FS = (0.10, 0.20, 0.30)
def main(d, res):
    os.makedirs(res, exist_ok=True); outp = os.path.join(res, "e7.jsonl")
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
            for auto in (60, 600):
                a = allocate(T, auto)
                teams = {}
                for i in T:
                    if i == "other": continue
                    sa = {"%.2f" % fr: billed_seconds([(s, s + (e - s) * (1 - fr)) for s, e in T[i]], auto) for fr in FS}
                    sa["0.00"] = billed_seconds(T[i], auto)
                    teams[str(i)] = {"standalone": sa, "charges": {k: a[k][i] for k in ("R2", "R3", "R4", "R5")}}
                out.write(json.dumps({"key": r["key"], "month": m, "auto": auto, "bill_s": a["bill_s"], "teams": teams}) + "\n")
        out.flush(); print(r["key"], "months", len(months), "%.0fs" % (time.time() - t0), flush=True)
    print("E7 DONE")
if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
