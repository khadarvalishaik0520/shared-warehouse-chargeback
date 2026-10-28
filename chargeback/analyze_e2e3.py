"""Pre-registered E2/E3 analysis (PLAN.md frozen definitions + Addendum 1). Usage: python3 analyze_e2e3.py <e2e3.jsonl>"""
import sys, json, statistics as st, collections
R = [json.loads(l) for l in open(sys.argv[1])]
def q(v, p):
    v = sorted(v); return v[min(len(v) - 1, int(p * (len(v) - 1) + 0.5))] if v else float("nan")
def summ(v): return "median %.1f%% (IQR %.1f–%.1f%%, n=%d)" % (100 * q(v, .5), 100 * q(v, .25), 100 * q(v, .75), len(v))
RULES = ("R2", "R3", "R4", "R5")
print("rows", len(R), "instances", len({r["key"] for r in R}))
for auto in (60, 300, 600, 30):
    A = [r for r in R if r["auto"] == auto]
    if not A: continue
    print("\n=== AUTO_SUSPEND %d s %s ===" % (auto, "(minimum can bind; R5 sampled)" if auto < 60 else ""))
    # E2: unassigned share per instance (summed over months)
    inst = collections.defaultdict(lambda: [0.0, 0.0])
    for r in A: inst[r["key"]][0] += r["unassigned_s"]; inst[r["key"]][1] += r["bill_s"]
    e2 = [u / b for u, b in inst.values() if b > 0]
    print("E2 unassigned share of bill per instance:", summ(e2))
    for kind in ("provisioned", "serverless"):
        v = [inst[k][0] / inst[k][1] for k in inst if k.startswith(kind) and inst[k][1] > 0]
        print("   %-11s %s" % (kind, summ(v)))
    # E3a: core violations (coalitions) and singleton overcharge (team charged above its standalone bill)
    for rule in RULES:
        viol = sum(r["core_viol"][rule] for r in A); chk = sum(r["coalitions_checked"] for r in A)
        months_any = sum(1 for r in A if r["core_viol"][rule] > 0)
        sing = sum(1 for r in A for t, c in r["charges"][rule].items() if c > r["standalone_s"][t] + 1e-6)
        teams = sum(len(r["charges"][rule]) for r in A)
        # E3b overcharge vs Shapley (share of bill moved), per instance-month
        dev = [sum(abs(r["charges"][rule][t] - r["charges"]["R5"][t]) for t in r["charges"]["R5"]) / 2 / r["bill_s"]
               for r in A if r["bill_s"] > 0]
        print("E3 %s: coalitions over standalone %d/%d (%.2f%%); instance-months with any %d/%d; "
              "teams charged above standalone %d/%d (%.1f%%); bill moved vs Shapley %s"
              % (rule, viol, chk, 100 * viol / max(chk, 1), months_any, len(A), sing, teams, 100 * sing / max(teams, 1), summ(dev)))
    # E3c volatility: CV of monthly charge for teams whose monthly exec seconds vary < 10%
    byteam = collections.defaultdict(list)
    for r in A:
        for t in r["exec_s"]: byteam[(r["key"], t)].append(r)
    cv = {k: [] for k in RULES}; n_stable = 0
    for (key, t), rs in byteam.items():
        if len(rs) < 2 or t == "other": continue
        ex = [r["exec_s"][t] for r in rs]
        if st.mean(ex) <= 0 or st.pstdev(ex) / st.mean(ex) >= 0.10: continue
        n_stable += 1
        for k in RULES:
            ch = [r["charges"][k][t] for r in rs]
            if st.mean(ch) > 0: cv[k].append(st.pstdev(ch) / st.mean(ch))
    print("E3c volatility (teams with stable own usage: %d): CV of monthly charge" % n_stable)
    for k in RULES: print("   %s %s" % (k, summ(cv[k])))
    print("R5 exact rows: %d/%d" % (sum(1 for r in A if r["r5_exact"]), len(A)))
