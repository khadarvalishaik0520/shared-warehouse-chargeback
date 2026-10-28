"""Independent recomputation of every SIGMOD paper number. Usage: verify_sigmod.py <results_dir> [--drop-feb]"""
import sys, json, statistics as st, collections
D = sys.argv[1]; DROP = "--drop-feb" in sys.argv
keep = lambda r: not (DROP and r["month"] == "2024-02")
E = [r for r in map(json.loads, open(D + "/e2e3.jsonl")) if keep(r)]
B = [r for r in map(json.loads, open(D + "/e4b.jsonl")) if keep(r)]
med = st.median
def pct(v, p):
    v = sorted(v); k = (len(v) - 1) * p; f = int(k); c = min(f + 1, len(v) - 1); return v[f] + (v[c] - v[f]) * (k - f)
print("DROP_FEB", DROP, "| instance-months per setting", collections.Counter(r["auto"] for r in E))
print("instances", len({r["key"] for r in E}), "team-months@60", sum(len(r["charges"]["R5"]) for r in E if r["auto"] == 60))
for a in (60, 300, 600, 30):
    A = [r for r in E if r["auto"] == a]
    inst = collections.defaultdict(lambda: [0, 0])
    for r in A: inst[r["key"]][0] += r["unassigned_s"]; inst[r["key"]][1] += r["bill_s"]
    sh = {k: u / b for k, (u, b) in inst.items()}
    out = ["E2 %d: median %.1f%% IQR %.1f-%.1f" % (a, 100 * med(sh.values()), 100 * pct(list(sh.values()), .25), 100 * pct(list(sh.values()), .75))]
    for kind in ("provisioned", "serverless"):
        out.append("%s %.1f%%" % (kind, 100 * med([v for k, v in sh.items() if k.startswith(kind)])))
    print(" | ".join(out))
    for rule in ("R2", "R3", "R4", "R5"):
        tm = [(c > r["standalone_s"][t] + 1e-6) for r in A for t, c in r["charges"][rule].items()]
        cv = sum(r["core_viol"][rule] for r in A); ch = sum(r["coalitions_checked"] for r in A)
        mv = [sum(abs(r["charges"][rule][t] - r["charges"]["R5"][t]) for t in r["charges"]["R5"]) / 2 / r["bill_s"] for r in A]
        print("  %s team-months over %d/%d=%.1f%% coalitions %d/%d=%.1f%% moved-vs-R5 median %.1f%%" % (rule, sum(tm), len(tm), 100 * sum(tm) / len(tm), cv, ch, 100 * cv / ch, 100 * med(mv)))
# E4a share shift 60->600
idx = {(r["key"], r["month"], r["auto"]): r for r in E}
for rule in ("R2", "R4", "R5"):
    d = []
    for (k, m, a), r in idx.items():
        if a != 60 or (k, m, 600) not in idx: continue
        s = idx[(k, m, 600)]
        for t in r["charges"][rule]:
            d.append(100 * abs(s["charges"][rule][t] / s["bill_s"] - r["charges"][rule][t] / r["bill_s"]))
    print("E4a %s share shift median %.1f pp p90 %.1f (n=%d)" % (rule, med(d), pct(d, .9), len(d)))
# volatility
for a in (60, 300, 600):
    A = [r for r in E if r["auto"] == a]; byt = collections.defaultdict(list)
    for r in A:
        for t in r["exec_s"]: byt[(r["key"], t)].append(r)
    cvs = collections.defaultdict(list); n = 0
    for (k, t), rs in byt.items():
        if len(rs) < 2 or t == "other": continue
        ex = [r["exec_s"][t] for r in rs]
        if st.mean(ex) <= 0 or st.pstdev(ex) / st.mean(ex) >= .1: continue
        n += 1
        for rule in ("R2", "R4", "R5"):
            c = [r["charges"][rule][t] for r in rs]
            if st.mean(c) > 0: cvs[rule].append(st.pstdev(c) / st.mean(c))
    print("vol %d: n=%d " % (a, n) + " ".join("%s %.1f%%" % (k, 100 * med(v)) for k, v in cvs.items()))
for a in (60, 600):
    A = [r for r in B if r["auto"] == a]; print("E4b %d: doubling cases %d" % (a, len(A)))
    for rule in ("R2", "R4", "R5"):
        cs = [(v[rule][0], v[rule][1]) for r in A for j, v in r["others"].items() if j != "other"]
        rise = [100 * (y - x) / x for x, y in cs if x > 0 and y > x * (1 + 1e-9) + 1e-6]
        print("   %s rises %d/%d = %.1f%% median rise %s" % (rule, len(rise), len(cs), 100 * len(rise) / len(cs), "%.1f%%" % med(rise) if rise else "-"))
