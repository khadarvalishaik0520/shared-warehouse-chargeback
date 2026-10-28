"""SIGMOD E1: four query-tagged teams share CB_SHARED (XS) for 60 min at AUTO_SUSPEND 60, then 60 min at 300.
Each phase starts at the top of an hour (metering is hourly) unless --now. Team schedules are seeded (seed 2026).
Truth = QUERY_HISTORY, QUERY_ATTRIBUTION_HISTORY, WAREHOUSE_EVENTS_HISTORY, WAREHOUSE_METERING_HISTORY (pull)."""
import sys, os, json, time, random, threading, datetime
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sf"))
from sf_wcp import connect, run, batch_queries, LADDER
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sf", "runs"); os.makedirs(OUT, exist_ok=True)
DUR = 3600
def schedule(team, rng):
    """(offset_s, schema, statement_name) list for one 60-min phase."""
    B = [n for n, _ in batch_queries()]; ev = []
    if team == "dash":     # bursts of 5 dashboard queries every ~4 min
        t = rng.uniform(0, 60)
        while t < DUR - 60: ev += [(t + k * 2, "TPCH", rng.choice(B)) for k in range(5)]; t += rng.uniform(180, 300)
    elif team == "batch":  # one heavier job every 15 min
        ev = [(60 + k * 900, "TPCH10", "top_cust") for k in range(4)]
    elif team == "adhoc":  # Poisson, mean gap 6 min
        t = rng.expovariate(1 / 360.0)
        while t < DUR: ev.append((t, "TPCH", rng.choice(B))); t += rng.expovariate(1 / 360.0)
    elif team == "trickle":  # tiny query every 2 min
        ev = [(30 + k * 120, "TPCH", "probe_point") for k in range(DUR // 120)]
    return sorted(ev)
SQL = dict(batch_queries() + LADDER)
def team_thread(team, auto, t0, evs, out, lock):
    cons = {s: connect("CB_SHARED", "cb_e1_a%d_%s" % (auto, team), schema=s) for s in ("TPCH", "TPCH10")}
    for off, schema, name in evs:
        dt = t0 + off - time.time()
        if dt > 0: time.sleep(dt)
        r = run(cons[schema], SQL[name]); r.update({"auto": auto, "team": team, "name": name, "planned": t0 + off})
        with lock: out.write(json.dumps(r) + "\n"); out.flush()
    for c in cons.values(): c.close()
def main(now=False):
    f = open(os.path.join(OUT, "e1_%d.jsonl" % time.time()), "a"); lock = threading.Lock()
    admin = connect("CB_SHARED", "cb_e1_admin", schema="TPCH"); cur = admin.cursor()
    for auto in (60, 300):
        cur.execute("alter warehouse CB_SHARED set auto_suspend = %d" % auto)
        try: cur.execute("alter warehouse CB_SHARED suspend")
        except Exception: pass
        t0 = time.time() + 30 if now else (int(time.time() // 3600) + 1) * 3600
        print("auto", auto, "phase starts", datetime.datetime.fromtimestamp(t0), flush=True)
        rng = random.Random(2026)                 # same schedule in both phases (only AUTO_SUSPEND differs)
        th = [threading.Thread(target=team_thread, args=(tm, auto, t0, schedule(tm, rng), f, lock))
              for tm in ("dash", "batch", "adhoc", "trickle")]
        [t.start() for t in th]; [t.join() for t in th]
        time.sleep(max(0, t0 + DUR - time.time()) + auto + 90)
    admin.close(); print("E1 DONE")
if __name__ == "__main__": main(now="--now" in sys.argv)
