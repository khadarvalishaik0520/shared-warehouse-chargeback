"""Billing validation (E1 a/b). Phase window = [first, last] workload statement of the phase (query ids
from our run file) plus AUTO_SUSPEND + 30 s. Within the window: actual running periods = Snowflake RESUME->SUSPEND events
that start in it; model periods = common/billing.py periods() over EVERY query the warehouse ran in it (any session).
Also: actual running seconds vs metered compute credits. Usage:
python3 validate_billing.py <truth dir> <run file .jsonl> <warehouse> <auto field name in run file>"""
import sys, os, csv, json, datetime as dt
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common.billing import periods
T, RUN, WH, AF = sys.argv[1:5]
ts = lambda s: dt.datetime.fromisoformat(s).timestamp()
QH = {r["QUERY_ID"]: r for r in csv.DictReader(open(os.path.join(T, "query_history.csv"))) if r["WAREHOUSE_NAME"] == WH}
EV = sorted((ts(r["TIMESTAMP"]), r["EVENT_NAME"]) for r in csv.DictReader(open(os.path.join(T, "events.csv")))
            if r["WAREHOUSE_NAME"] == WH and r["EVENT_NAME"] in ("RESUME_WAREHOUSE", "SUSPEND_WAREHOUSE"))
act = []; cur = None
for t, n in EV:
    if n == "RESUME_WAREHOUSE" and cur is None: cur = t
    elif n == "SUSPEND_WAREHOUSE" and cur is not None: act.append((cur, t)); cur = None
runs = [json.loads(l) for l in open(RUN)]
xs = lambda r: (ts(r["END_TIME"]) - float(r["EXECUTION_TIME"]) / 1000.0, ts(r["END_TIME"]))
for auto in sorted({r[AF] for r in runs}):
    mine = [QH[r["qid"]] for r in runs if r[AF] == auto and r.get("qid") in QH]
    lo = min(ts(r["START_TIME"]) for r in mine) - 5; hi = max(ts(r["END_TIME"]) for r in mine) + auto + 30
    A = [(s, e) for s, e in act if lo <= s <= hi]
    iv = sorted(xs(r) for r in QH.values() if r["EXECUTION_STATUS"] == "SUCCESS" and lo <= ts(r["START_TIME"]) <= hi)
    other = sum(1 for r in QH.values() if lo <= ts(r["START_TIME"]) <= hi) - len(mine)
    M = periods(iv, auto); mm = sum(max(60, e - s) for s, e in M); ma = sum(e - s for s, e in A)
    ov = sum(max(0, min(e1, e2) - max(s1, s2)) for s1, e1 in M for s2, e2 in A)
    tails = sorted(e - max(qe for qs, qe in iv if s - 1 <= qe <= e + 1) for s, e in A if any(s - 1 <= qe <= e + 1 for qs, qe in iv))
    print("auto %d: our statements %d (+%d other statements on the warehouse) | model %d periods, %.0f s | actual %d periods, %.0f s | "
          "model/actual %.3f | overlap %.1f%% | tail after last query median %.1f s (min %.1f, max %.1f)"
          % (auto, len(mine), other, len(M), mm, len(A), ma, mm / ma, 100 * ov / ma, tails[len(tails) // 2], tails[0], tails[-1]))
ME = [r for r in csv.DictReader(open(os.path.join(T, "metering.csv"))) if r["WAREHOUSE_NAME"] == WH]
run_s = sum(e - s for s, e in act); cred = sum(float(r["CREDITS_USED_COMPUTE"]) for r in ME)
print("%s: actual running %.0f s in total, metered compute %.4f credits -> %.3f credits per running hour" % (WH, run_s, cred, cred / (run_s / 3600)))
