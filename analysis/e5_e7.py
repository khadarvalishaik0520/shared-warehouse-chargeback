"""E5 (isolated growth) and E7 (assumption A1: a team alone runs faster) summaries, paper Sections 6.4 and 6.6.
Usage: python3 analysis/e5_e7.py <results dir>     (the 2024-02 stub month is dropped, Deviation 2)"""
import sys, json, statistics as st
D = sys.argv[1] if len(sys.argv) > 1 else "results"
E5 = [r for r in map(json.loads, open(D + "/e5.jsonl")) if r["month"] != "2024-02"]
print("== E5: one team adds 10 isolated 1 s queries; share of (grower, named bystander) pairs whose charge rises")
for a in (60, 600):
    for k in ("R2", "R4", "R5"):
        v = [o[k][1] > o[k][0] + 1e-6 for r in E5 if r["auto"] == a for j, o in r["others"].items() if j != "other"]
        ev = [any(o[k][1] > o[k][0] + 1e-6 for j, o in r["others"].items() if j != "other") for r in E5 if r["auto"] == a]
        print("  auto %3d  %s  pairs %5.1f%% of %d   events with any rise %5.1f%% of %d" % (a, k, 100 * sum(v) / len(v), len(v), 100 * sum(ev) / len(ev), len(ev)))
E7 = [r for r in map(json.loads, open(D + "/e7.jsonl")) if r["month"] != "2024-02"]
print("== E7: named team-months charged above the shortened standalone cost")
for a in (60, 600):
    for f in ("0.10", "0.20", "0.30"):
        row = []
        for k in ("R2", "R3", "R4", "R5"):
            v = [t["charges"][k] > t["standalone"][f] + 1e-6 for r in E7 if r["auto"] == a for t in r["teams"].values()]
            row.append("%s %4.1f%%" % (k, 100 * sum(v) / len(v)))
        ex = [t["charges"]["R5"] / t["standalone"][f] - 1 for r in E7 if r["auto"] == a for t in r["teams"].values() if t["charges"]["R5"] > t["standalone"][f] + 1e-6]
        print("  auto %3d  f=%s  %s   R5 excess median %.1f%%" % (a, f, "  ".join(row), 100 * st.median(ex) if ex else 0))
