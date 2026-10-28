"""Pre-registered sensitivity (frozen definitions, PLAN.md): query intervals without compile time. Prints the E2/E3
headline numbers for the main run and the no-compile run side by side (stub month 2024-02 dropped, Deviation 2).
Usage: python3 analysis/nocompile.py <results dir>"""
import sys, json, statistics as st, collections
D = sys.argv[1] if len(sys.argv) > 1 else "results"
def load(f): return [r for r in map(json.loads, open(D + "/" + f)) if r["month"] != "2024-02"]
M, N = load("e2e3.jsonl"), load("e2e3_nocompile.jsonl")
def summary(E, a):
    A = [r for r in E if r["auto"] == a]; inst = collections.defaultdict(lambda: [0.0, 0.0])
    for r in A: inst[r["key"]][0] += r["unassigned_s"]; inst[r["key"]][1] += r["bill_s"]
    out = {"instances": len(inst), "unassigned_median": 100 * st.median(u / b for u, b in inst.values())}
    for k in ("R2", "R3", "R4", "R5"):
        tm = [c > r["standalone_s"][t] + 1e-6 for r in A for t, c in r["charges"][k].items()]
        out[k] = 100 * sum(tm) / len(tm)
    out["R5_coalition_viol"] = sum(r["core_viol"]["R5"] for r in A); out["coalitions"] = sum(r["coalitions_checked"] for r in A)
    return out
for a in (60, 300, 600):
    m, n = summary(M, a), summary(N, a)
    print("auto %3d  %-12s instances %d  unassigned median %.1f%%  over standalone: R2 %.1f%% R3 %.1f%% R4 %.1f%% R5 %.1f%%  R5 coalition violations %d/%d"
          % (a, "main", m["instances"], m["unassigned_median"], m["R2"], m["R3"], m["R4"], m["R5"], m["R5_coalition_viol"], m["coalitions"]))
    print("          %-12s instances %d  unassigned median %.1f%%  over standalone: R2 %.1f%% R3 %.1f%% R4 %.1f%% R5 %.1f%%  R5 coalition violations %d/%d"
          % ("no compile", n["instances"], n["unassigned_median"], n["R2"], n["R3"], n["R4"], n["R5"], n["R5_coalition_viol"], n["coalitions"]))
