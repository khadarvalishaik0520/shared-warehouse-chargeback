"""Redset -> per-instance query intervals for the chargeback study (data preparation only, no results).
Interval on the (counterfactual) warehouse = [arrival + queue, arrival + queue + compile + execution].
Pre-registered choice; sensitivity variant drops compile. Aborted queries are kept (they were billed); result-cache
hits with zero execution are dropped (they do not keep a warehouse running).
Usage: python3 redset_load.py <redset_dir> <out_dir>      (re-runnable; skips finished instances)"""
import sys, os, glob, json, duckdb
src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
con = duckdb.connect(); con.execute("SET threads TO 2")
inv = open(os.path.join(out, "inventory.jsonl"), "a")
done = {l.split('"key": "')[1].split('"')[0] for l in open(os.path.join(out, "inventory.jsonl"))} if os.path.getsize(os.path.join(out, "inventory.jsonl")) else set()
for kind in ("serverless", "provisioned"):
    for f in sorted(glob.glob(os.path.join(src, kind, "parts", "*.parquet")), key=lambda p: int(os.path.basename(p).split(".")[0])):
        if not os.path.exists(f + ".ok"): continue          # still downloading
        key = "%s/%s" % (kind, os.path.basename(f).split(".")[0])
        if key in done: continue
        dst = os.path.join(out, key.replace("/", "_") + ".parquet")
        con.execute(f"""copy (
            select user_id as team,
                   epoch(arrival_timestamp) + coalesce(queue_duration_ms,0)/1000.0 as s,
                   epoch(arrival_timestamp) + (coalesce(queue_duration_ms,0) + coalesce(compile_duration_ms,0) + execution_duration_ms)/1000.0 as e,
                   coalesce(compile_duration_ms,0)/1000.0 as compile_s,
                   query_type, was_aborted
            from read_parquet('{f}')
            where execution_duration_ms is not null and not (was_cached and coalesce(execution_duration_ms,0) = 0)
            order by s) to '{dst}' (format parquet)""")
        r = con.execute(f"""select count(*), count(distinct team), min(s), max(e), sum(e-s)/3600.0,
                             (select any_value(cluster_size) from read_parquet('{f}')),
                             (select count(*) from read_parquet('{f}'))
                            from read_parquet('{dst}')""").fetchone()
        rec = {"key": key, "kind": kind, "queries_kept": r[0], "teams": r[1], "t0": r[2], "t1": r[3],
               "days": round((r[3] - r[2]) / 86400, 1) if r[2] else 0, "exec_h": round(r[4] or 0, 1),
               "cluster_size": r[5], "rows_raw": r[6]}
        inv.write(json.dumps(rec) + "\n"); inv.flush(); print(rec, flush=True)
print("LOAD PASS DONE")
