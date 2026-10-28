"""E4b analysis (PLAN.md Addendum 3): when one team doubles, how often does another team's charge rise, per rule?"""
import sys, json, statistics as st
R = [json.loads(l) for l in open(sys.argv[1])]
print("instances", len({r["key"] for r in R}), "doubling cases", len(R))
for auto in (60, 600):
    A = [r for r in R if r["auto"] == auto]
    print("\nAUTO_SUSPEND %d s: %d doubling cases" % (auto, len(A)))
    for k in ("R2", "R4", "R5"):
        cases = [(v[k][0], v[k][1]) for r in A for j, v in r["others"].items() if j != "other"]
        rise = [100 * (b - a) / a for a, b in cases if b > a * (1 + 1e-9) + 1e-6 and a > 0]
        print("  %s: other team's charge rises in %d of %d cases (%.2f%%); median rise when it happens %s"
              % (k, len(rise), len(cases), 100 * len(rise) / max(len(cases), 1), ("%.1f%%" % st.median(rise)) if rise else "-"))
