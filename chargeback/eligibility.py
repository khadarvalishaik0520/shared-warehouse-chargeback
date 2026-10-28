"""Applies the frozen inclusion rule (>= 2 teams with >= 1% of execution seconds each, >= 7 days). Data check only.
Re-runnable; appends to eligibility.jsonl.  Usage: python3 eligibility.py <redset_iv dir>"""
import json, os, sys, duckdb
d = sys.argv[1]; outp = os.path.join(d, "eligibility.jsonl")
done = {json.loads(l)["key"] for l in open(outp)} if os.path.exists(outp) else set()
c = duckdb.connect(); c.execute("SET threads TO 2"); out = open(outp, "a")
for l in open(os.path.join(d, "inventory.jsonl")):
    r = json.loads(l)
    if r["key"] in done: continue
    rec = {"key": r["key"], "kind": r["kind"], "days": r["days"], "teams_all": r["teams"], "teams_1pct": 0}
    if r["teams"] >= 2 and r["days"] >= 7:
        f = os.path.join(d, r["key"].replace("/", "_") + ".parquet")
        sh = [x for (x,) in c.execute(f"select sum(e-s) from '{f}' group by team").fetchall()]
        tot = sum(sh) or 1; rec["teams_1pct"] = sum(1 for x in sh if x / tot >= 0.01)
    rec["eligible"] = rec["teams_1pct"] >= 2 and r["days"] >= 7
    out.write(json.dumps(rec) + "\n"); out.flush(); print(rec["key"], rec["eligible"], flush=True)
print("ELIG DONE")
