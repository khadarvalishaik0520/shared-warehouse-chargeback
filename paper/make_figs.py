"""Figures for the SIGMOD paper, from the pre-registered result files only."""
import json, collections, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, __import__("os").path.abspath(__import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)), ".."))); from common.billing import periods
import os
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
U = os.path.join(ROOT, "chargeback", "results") + "/"
plt.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42, "font.size": 8, "font.family": "serif", "axes.spines.top": False, "axes.spines.right": False,
                     "figure.dpi": 200, "savefig.bbox": "tight", "savefig.pad_inches": 0.02})
INK, MUTED, C = "#222222", "#888888", ["#2f6db3", "#d9822b", "#3a9e5b", "#b0413e", "#7a5aa6"]
R = [r for r in map(json.loads, open(U + "e2e3.jsonl")) if r["month"] != "2024-02"]  # Deviation 2: drop 5-hour stub month
# Fig 2: unassigned share per instance by AUTO_SUSPEND
fig, ax = plt.subplots(figsize=(3.3, 1.7)); data = []
for auto in (60, 300, 600):
    inst = collections.defaultdict(lambda: [0.0, 0.0])
    for r in R:
        if r["auto"] == auto: inst[r["key"]][0] += r["unassigned_s"]; inst[r["key"]][1] += r["bill_s"]
    data.append([100 * u / b for u, b in inst.values() if b > 0])
bp = ax.boxplot(data, orientation="horizontal", widths=0.5, patch_artist=True, medianprops={"color": INK}, flierprops={"markersize": 2, "markeredgecolor": MUTED})
for p in bp["boxes"]: p.set_facecolor("#cfe0f3"); p.set_edgecolor(C[0])
ax.set_yticks([1, 2, 3], ["60 s", "300 s", "600 s\n(default)"]); ax.set_xlabel("Share of the bill left unassigned by execution-time attribution (%)")
ax.set_xlim(0, 100); fig.savefig("figs/e2_unassigned.pdf")
# Fig 3: teams charged above standalone, per rule and setting
fig, ax = plt.subplots(figsize=(3.3, 1.75)); rules = [("R2", "Proportional"), ("R3", "Equal split"), ("R4", "Marginal"), ("R5", "Shapley")]
w = 0.26
for i, auto in enumerate((60, 300, 600)):
    A = [r for r in R if r["auto"] == auto]; vals = []
    for k, _ in rules:
        sing = sum(1 for r in A for t, c in r["charges"][k].items() if c > r["standalone_s"][t] + 1e-6)
        vals.append(100 * sing / sum(len(r["charges"][k]) for r in A))
    xs = [j + (i - 1) * w for j in range(4)]
    ax.bar(xs, vals, w, color=C[i], label="%d s" % auto)
    for x, v in zip(xs, vals):
        if v == 0: ax.text(x, 0.8, "0", ha="center", fontsize=6, color=INK)
ax.set_xticks(range(4), ["Proportional", "Equal\nsplit", "Marginal", "Shapley"], fontsize=7); ax.set_ylabel("Team-months charged\nabove standalone (%)")
ax.set_ylim(0, 55); ax.legend(frameon=False, fontsize=7, title="AUTO_SUSPEND", title_fontsize=7, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.22)); fig.savefig("figs/e3_overcharge.pdf")
# Fig 1: worked example (Section 3) -- three teams, AUTO_SUSPEND 60 s, coverage and the per-second Shapley split
T = {"Dash": [(0, 2), (100, 102), (200, 202)], "Batch": [(30, 150)], "Adhoc": [(400, 402)]}; auto = 60
fig, ax = plt.subplots(figsize=(3.3, 1.6))
for i, (t, v) in enumerate(T.items()):
    y = 4 - i
    for s_, e_ in v:
        ax.barh(y, max(e_ - s_, 2), left=s_, height=0.5, color=C[i]); ax.barh(y, auto, left=e_, height=0.5, color=C[i], alpha=0.25)
    ax.text(-8, y, t, ha="right", va="center", fontsize=7)
cov = {t: periods(v, auto) for t, v in T.items()}
pts = sorted({x for v in cov.values() for p in v for x in p})
for a_, b_ in zip(pts, pts[1:]):
    who = [i for i, t in enumerate(T) if any(p0 <= a_ and b_ <= p1 for p0, p1 in cov[t])]
    if not who: continue
    h = 0.5 / len(who)
    for k, i in enumerate(who): ax.barh(1 - 0.25 + h * (k + 0.5), b_ - a_, left=a_, height=h, color=C[i], alpha=0.85)
    if b_ - a_ >= 8: ax.text((a_ + b_) / 2, 0.45 if b_ - a_ >= 25 else 0.12, "%d" % (b_ - a_) + ("/%d" % len(who) if len(who) > 1 else ""), ha="center", fontsize=5.5, color=INK)
ax.text(-8, 1, "Split", ha="right", va="center", fontsize=7)
ax.set_yticks([]); ax.set_ylim(-0.05, 4.5); ax.set_xlabel("Time (s)"); ax.set_xlim(0, 470)
ax.spines["left"].set_visible(False); fig.savefig("figs/example.pdf")
# Fig 5 (exploratory): who pays more under Shapley than proportional, by tail intensity (standalone / execution seconds)
fig, ax = plt.subplots(figsize=(3.3, 1.6))
for i, auto in enumerate((60, 600)):
    pts_ = sorted((r["standalone_s"][t] / r["exec_s"][t], 100 * (r["charges"]["R5"][t] - r["charges"]["R2"][t]) / r["bill_s"])
                  for r in R if r["auto"] == auto for t in r["charges"]["R5"] if t != "other" and r["exec_s"][t] > 0)
    n = len(pts_); xs, ys, lo, hi = [], [], [], []
    for d in range(10):
        b = sorted(y for _, y in pts_[d * n // 10:(d + 1) * n // 10]); import statistics; qs = statistics.quantiles(b, n=4, method="inclusive")
        xs.append(d + 1); ys.append(statistics.median(b)); lo.append(qs[0]); hi.append(qs[2])
    ax.plot(xs, ys, "-o", ms=2.5, color=C[i * 2], label="%d s" % auto); ax.fill_between(xs, lo, hi, color=C[i * 2], alpha=0.15, lw=0)
ax.axhline(0, color=MUTED, lw=0.6); ax.set_xticks(range(1, 11))
ax.set_xlabel("Decile of tail intensity (standalone cost / execution time)"); ax.set_ylabel("Shapley minus\nproportional (pp)")
ax.legend(frameon=False, fontsize=7, title="AUTO_SUSPEND", title_fontsize=7, loc="upper left"); fig.savefig("figs/who_pays.pdf")
# Fig 4: bystander rises -- E4b (doubling in place) and E5 (10 isolated queries)
fig, axes = plt.subplots(1, 2, figsize=(3.4, 1.45), sharey=True)
for ax, (fn, title) in zip(axes, (("e4b.jsonl", "Team doubles in place"), ("e5.jsonl", "Team adds 10 isolated queries"))):
    E = [r for r in map(json.loads, open(U + fn)) if r["month"] != "2024-02"]
    for i, auto in enumerate((60, 600)):
        A = [r for r in E if r["auto"] == auto]; vals = []
        for k in ("R2", "R4", "R5"):
            cases = [(v[k][0], v[k][1]) for r in A for j, v in r["others"].items() if j != "other"]
            vals.append(100 * sum(1 for a, b in cases if b > a * (1 + 1e-9) + 1e-6) / len(cases))
        xs = [j + (i - 0.5) * 0.36 for j in range(3)]; ax.bar(xs, vals, 0.36, color=C[i * 2], label="%d s" % auto)
        for x, v in zip(xs, vals): ax.text(x, v + 1.5, "%.0f" % v, ha="center", fontsize=5.5)
    ax.set_xticks(range(3), ["Prop.", "Marg.", "Shapley"], fontsize=6.5); ax.set_title(title, fontsize=6.5)
axes[0].set_ylabel("Bystander charge\nrises (%)"); axes[0].set_ylim(0, 85)
axes[0].legend(frameon=False, fontsize=6, ncol=1, title="AUTO_SUSPEND", title_fontsize=6, loc="upper left")
fig.savefig("figs/e4_bystander.pdf")
print("figures written")
# Fig (exploratory): how far each named team's share moves from Shapley under each rule, 600 s
fig, ax = plt.subplots(figsize=(3.3, 1.6))
A6 = [r for r in R if r["auto"] == 600]
for i, (k, lab_) in enumerate((("R2", "Proportional"), ("R3", "Equal split"), ("R4", "Marginal"))):
    v = sorted(100 * abs(r["charges"][k][t] - r["charges"]["R5"][t]) / r["bill_s"] for r in A6 for t in r["charges"]["R5"] if t != "other")
    ax.step(v, [(j + 1) / len(v) for j in range(len(v))], where="post", color=C[i], label=lab_, lw=1.2)
ax.set_xlabel("|Share under rule $-$ Shapley share| (percentage points of the bill)"); ax.set_ylabel("Share of\nteam-months")
ax.set_xlim(0, 60); ax.set_ylim(0, 1.02); ax.legend(frameon=False, fontsize=7, loc="lower right"); fig.savefig("figs/share_gap.pdf")
