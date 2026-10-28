"""SIGMOD E6 (PLAN.md Addendum 4): run the paper's chargeback SQL inside Snowflake and compare with the Python sweep;
then time it on a 1M-row synthetic month. Writes sf/runs/e6_<ts>.json. Usage (Mac): python sf/sf_sql_check.py"""
import os, sys, json, time, csv
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, ".."))
from sf_wcp import connect
from common.billing import shapley_sweep
LISTING = """
WITH iv AS (SELECT team, s, e + {a} AS e FROM {tbl}),
ord AS (SELECT team, s, e, MAX(e) OVER (PARTITION BY team
          ORDER BY s, e ROWS BETWEEN UNBOUNDED PRECEDING
          AND CURRENT ROW) AS cm FROM iv),
isl AS (SELECT team, s, e, CASE WHEN s <= LAG(cm) OVER (PARTITION
          BY team ORDER BY s, e) THEN 0 ELSE 1 END AS new FROM ord),
grp AS (SELECT team, s, e, SUM(new) OVER (PARTITION BY team ORDER
          BY s, e ROWS UNBOUNDED PRECEDING) AS k FROM isl),
cover AS (SELECT team, MIN(s) s, MAX(e) e FROM grp GROUP BY team, k),
ev AS (SELECT t, SUM(d) d FROM (SELECT s t, 1 d FROM cover UNION ALL
          SELECT e, -1 FROM cover) x GROUP BY t),
cnt AS (SELECT t, SUM(d) OVER (ORDER BY t ROWS UNBOUNDED PRECEDING)
          n, LEAD(t) OVER (ORDER BY t) t2 FROM ev),
w AS (SELECT t, CASE WHEN n > 0 THEN (t2 - t) / n ELSE 0 END x
          FROM cnt),
g AS (SELECT t, SUM(x) OVER (ORDER BY t ROWS UNBOUNDED PRECEDING)
          - x AS g FROM w)
SELECT c.team, SUM(ge.g - gs.g) AS charge_s FROM cover c
  JOIN g gs ON gs.t = c.s JOIN g ge ON ge.t = c.e GROUP BY c.team
"""
FALLBACK = lambda q: q.replace("ROWS UNBOUNDED PRECEDING", "ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW")
out = {"started": time.time(), "notes": []}
con = connect("CB_SHARED", "wcp_e6_sqlcheck", schema="TPCH10"); cur = con.cursor()
cur.execute("alter warehouse CB_SHARED set auto_suspend = 60")
def run(q):
    for variant, sql in (("as printed", q), ("fallback frames", FALLBACK(q))):
        try:
            t = time.time(); cur.execute(sql); rows = cur.fetchall(); return rows, time.time() - t, variant, cur.sfqid
        except Exception as ex:
            out["notes"].append("%s failed: %s" % (variant, str(ex)[:300]))
    raise SystemExit("both variants failed: %s" % out["notes"])
# 1) correctness on the E1 run's own query history
truth = os.path.join(HERE, "truth", "query_history.csv"); from datetime import datetime
P = lambda x: datetime.fromisoformat(x).timestamp()
for a, tagp in ((60, "cb_e1_a60_"), (300, "cb_e1_a300_")):
    T = {}
    for r in csv.DictReader(open(truth)):
        if r["WAREHOUSE_NAME"] == "CB_SHARED" and r["QUERY_TAG"].startswith(tagp):
            e = P(r["END_TIME"]); T.setdefault(r["QUERY_TAG"][len(tagp):], []).append((e - int(r["EXECUTION_TIME"]) / 1000.0, e))
    cur.execute("create or replace temporary table e6_q (team varchar, s double, e double)")
    cur.executemany("insert into e6_q values (%s, %s, %s)", [(t, s, e) for t, v in T.items() for s, e in v])
    rows, dt, variant, qid = run(LISTING.format(a=a, tbl="e6_q"))
    ref = shapley_sweep({t: sorted(v) for t, v in T.items()}, a); got = {t: float(c) for t, c in rows}
    out["e1_a%d" % a] = {"variant": variant, "qid": qid, "elapsed_s": dt, "teams": {t: [got.get(t), ref[t]] for t in ref},
                         "max_abs_diff_s": max(abs(got.get(t, 0) - ref[t]) for t in ref)}
    print("E1 a=%d: %s, max diff %.2e s, %.2f s" % (a, variant, out["e1_a%d" % a]["max_abs_diff_s"], dt), flush=True)
# 2) timing on 1M synthetic rows (one month, 10 teams, exponential 5 s run times)
cur.execute("""create or replace temporary table e6_syn as
  select 't' || mod(i, 10) as team, s, s - 5 * ln(uniform(1e-9::float, 1::float, random())) as e
  from (select seq4() as i, uniform(0::float, 2592000::float, random()) as s from table(generator(rowcount => 1000000)))""")
for a in (600, 60):
    rows, dt, variant, qid = run(LISTING.format(a=a, tbl="e6_syn"))
    out["syn_a%d" % a] = {"variant": variant, "qid": qid, "elapsed_s": dt, "teams": len(rows), "sum_charge_s": sum(float(c) for _, c in rows)}
    print("synthetic 1M a=%d: %s, %.2f s" % (a, variant, dt), flush=True)
cur.execute("alter warehouse CB_SHARED suspend")
out["finished"] = time.time()
os.makedirs(os.path.join(HERE, "runs"), exist_ok=True); f = os.path.join(HERE, "runs", "e6_%d.json" % time.time())
json.dump(out, open(f, "w"), indent=1); print("notes:", out["notes"]); print("E6 DONE ->", f)
