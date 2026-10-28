"""Exploratory (not pre-registered) analyses for the expanded SIGMOD draft. Feb stub dropped (Deviation 2)."""
import json, statistics as st, collections, math
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
D = os.path.join(ROOT, "chargeback", "results") + "/"
E = [r for r in map(json.loads, open(D + "e2e3.jsonl")) if r["month"] != "2024-02"]
def pct(v, p):
    v = sorted(v); k = (len(v) - 1) * p; f = int(k); c = min(f + 1, len(v) - 1); return v[f] + (v[c] - v[f]) * (k - f)
for a in (60, 300, 600):
    A = [r for r in E if r["auto"] == a]
    for rule in ("R2", "R3", "R4"):
        ex = [100 * (c / r["standalone_s"][t] - 1) for r in A for t, c in r["charges"][rule].items() if c > r["standalone_s"][t] + 1e-6]
        print(a, rule, "overcharged team-months excess over standalone: median %.0f%% p90 %.0f%%" % (st.median(ex), pct(ex, .9)))
    # who pays more under Shapley than proportional: tail intensity = standalone / exec
    x, y = [], []
    for r in A:
        for t in r["charges"]["R5"]:
            if t == "other" or r["exec_s"][t] <= 0: continue
            x.append(r["standalone_s"][t] / r["exec_s"][t]); y.append((r["charges"]["R5"][t] - r["charges"]["R2"][t]) / r["bill_s"])
    hi = [b for a_, b in zip(x, y) if a_ > st.median(x)]; lo = [b for a_, b in zip(x, y) if a_ <= st.median(x)]
    print(a, "tail-intensity median %.1f; Shapley-minus-proportional share: high-tail median %+.1f pp, low-tail %+.1f pp" % (st.median(x), 100 * st.median(hi), 100 * st.median(lo)))
    # concentration: share of bill the largest team pays
    # bill split overview: unassigned vs teams
    nteams = collections.Counter(min(len(r["charges"]["R5"]), 6) for r in A)
    print(a, "teams per instance-month (6 = 6+):", sorted(nteams.items()))
json.dump([(r["standalone_s"][t] / r["exec_s"][t], (r["charges"]["R5"][t] - r["charges"]["R2"][t]) / r["bill_s"]) for r in E if r["auto"] == 600 for t in r["charges"]["R5"] if t != "other" and r["exec_s"][t] > 0],
          open(os.path.join(ROOT, "chargeback", "results", "who_pays_600.json"), "w"))
