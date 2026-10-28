# Pre-registration and deviation log

This file is the study plan as written during the work; each addendum and deviation is dated when it was written
(US Eastern time). The timestamps are the author's own and were not lodged with an external registry. The repository
was published after the study, so its history starts at publication. Paths were renamed at publication: sigmod27_chargeback/ is chargeback/, and verify/*.py is analysis/*.py
(verify/test_sql2.py is tests/test_sql.py). The file is reproduced verbatim except for 4 short phrases that named a separate study
by the author; those are replaced by text in [square brackets]. The Schedule section is as originally planned; the work ran
ahead of it and was done by a single author. Experiment ids: E1 billing validation on Snowflake, E2 unassigned share,
E3 fairness of the rules, E4b/E5 bystander tests (a team doubles / adds isolated queries), E6 the chargeback SQL inside
Snowflake, E7 sensitivity to assumption A1. The first E2/E3 run had an engine bug (Deviation 1); its output is not
reported and the re-run is.

---

# [Study plan] — Who Pays for Idle? Fair Chargeback for Shared Cloud Data Warehouses
SIGMOD 2027 Industrial Track · due **Tue Nov 24, 2026, 11:59 PM AoE** · ACM sigconf, 12 pp + refs · author list frozen at submission

## Question (and only this question)
Given ONE shared warehouse and its invoice, how should the bill be split across the teams that use it?
Out of scope here (belongs to [a separate study]): whether teams should share, which warehouses should exist, sizing.

## Evidence (no overlap with [a separate study])
- Main fleet evidence: **Redset** (3 months, per-user query history, 200 serverless + 200 provisioned Redshift instances).
  Teams = user_id within an instance. Redshift's own billing differs (provisioned = node-hours; serverless = RPU-seconds),
  so each instance is replayed as a counterfactual per-second warehouse at fixed size. State this plainly in the paper.
- Snowflake study (own run, not reused by [a separate study]): 4 query-tagged "teams" with different arrival patterns
  (dashboard bursts, hourly batch, ad hoc, trickle) on ONE XS warehouse, ~2 h, AUTO_SUSPEND 60 s and 300 s.
  Ground truth: WAREHOUSE_METERING_HISTORY + QUERY_ATTRIBUTION_HISTORY.
- Snowset: not used.

## Technical core (status 2026-10-19)
- Cost game c(S) = billed seconds if only S's queries ran on the warehouse (same timing, fixed size).
- Observation (verified on 1,600 random instances, proof to write): when AUTO_SUSPEND >= 60 s the 60 s resume minimum
  never binds, so billed(S) = measure of the union of [start, end+auto] over S's queries -> coverage game ->
  submodular -> Shapley is in the core and is exact in O(m log m) by a sweep (each billed second split equally
  among the teams covering it). Sweep vs brute-force Shapley: max diff 3e-13 s; 0 core violations.
- When AUTO_SUSPEND < 60 s the minimum binds and the sweep is off (up to ~170 s on test instances) -> need an extension.
- Open: queueing/slowdown when teams overlap breaks "same timing"; quantify on the Snowflake run.

## Frozen definitions (2026-10-19 23:15 ET, before any E2–E4 number was computed; only a data inventory had been run)
- Query interval on the counterfactual warehouse: [arrival + queue, arrival + queue + compile + execution].
  Sensitivity: without compile. Result-cache hits with zero execution are dropped; aborted queries kept.
- Team = Redset user_id within one instance.
- Instance inclusion: >= 2 teams that each have >= 1% of the instance's execution seconds, and >= 7 days of history.
  Inventory at freeze time (39 of 400 instances loaded): 20 met ">= 2 teams and >= 7 days" before the 1% rule.
  Full inventory after loading all 400 (2026-10-19 23:40, rule applied, no results computed): 95 eligible instances
  (76 provisioned, 19 serverless); teams per instance with >= 1% share: 2:30, 3:17, 4:12, 5:12, 6:9, 7:4, 8:6, 9:2, 10+:3.
- Billing replay: fixed size; AUTO_SUSPEND grid {60, 300, 600 s} as main (Snowflake default is 600 s);
  {30 s} reported separately as the case where the resume minimum binds (see PROOF_NOTES.md).
- Billing month = calendar month (Redset spans Mar–May 2024). Volatility = coefficient of variation of a team's monthly
  charge, reported only for teams whose monthly execution seconds vary < 10% across months (own usage roughly fixed).
- Rules compared: (R1) execution-only attribution, remainder unassigned; (R2) R1 + remainder split by execution share
  (= proportional); (R3) equal split; (R4) leave-one-out marginal, rescaled to the bill; (R5) Shapley (sweep, a >= 60).

## Addendum 1 (2026-10-20 00:10 ET, implementation choices fixed before any real-data E2/E3 run)
- Teams below the 1% execution share are pooled into one "other" team (so the bill still sums; they are not reported).
- Coalition checks for core violations: all coalitions when <= 10 teams in the month; otherwise all singletons,
  all pairs and all leave-one-out complements.
- AUTO_SUSPEND = 30 s (minimum can bind): R5 = permutation-sampled Shapley, 2,000 permutations, seed 0; flagged approximate.
- Months with < 2 teams active are skipped. Runner: run_e2e3.py; tested only on synthetic data before the real run.

## Addendum 2 (2026-10-20 07:20 ET, E1 design fixed before any Snowflake run)
- Warehouse CB_SHARED (XS, created for this paper only, under CD_MONITOR). Two 60-min phases from the top of an hour:
  AUTO_SUSPEND 60 then 300, identical seeded schedules (seed 2026). Teams (query tags cb_e1_a<auto>_<team>):
  dash = bursts of 5 dashboard queries every 3-5 min (TPCH SF1); batch = one join job every 15 min (TPCH10);
  adhoc = Poisson, mean gap 6 min (TPCH SF1); trickle = one point query every 2 min. Result cache off.
- Truth (pulled the morning after, before the trial ends ~Nov 7): ACCOUNT_USAGE query_history, query_attribution_history,
  warehouse_events_history, warehouse_metering_history.
- E1 metrics: (a) model billed seconds (common/billing.py on QUERY_HISTORY execution intervals) vs metered credits,
  per hour and total; (b) actual suspend tail after the last query vs AUTO_SUSPEND (events history);
  (c) per-team charges under R1-R5 and Snowflake's own attribution; R2-R5 must sum to the metered invoice after
  scaling by metered/model (scaling factor reported).
- Budget estimate 1-2 credits. Script: sigmod27_chargeback/sf_e1.py.

## Deviation 1 (2026-10-20 13:45 ET, after the first full E2/E3 run) — disclose in the paper
- Bug found: R1 summed raw execution seconds per team. Redshift runs many queries concurrently, so the sum exceeded
  the billed time and the "unassigned share" came out negative (median -54% at 60 s). That contradicts the frozen
  definition (attribution assigns execution time; it cannot exceed busy time).
- Fix: R1 now splits each busy second equally among the queries running in it (native attribution splits concurrent
  time by resource use; Redset has no per-query resource use, so equal split is our stated approximation).
  Sum of R1 = busy seconds exactly (tested). R2 (proportional) uses these shares, so R2 also changes.
- Unchanged by the fix: R3, R4, R5, standalone costs, all coalition costs.
- First-run output kept as results/e2e3_run1_bug.jsonl. Full re-run with the fixed engine; the re-run is the reported one.
- Observed in run 1 and NOT affected by the fix (stated now so it cannot drift): R5 had 0 coalitions over standalone
  at 60/300/600 s (29,262 checked each), consistent with Theorem 1; 94 of the 95 eligible instances produced rows
  (one had < 2 active teams in every month).

## Addendum 3 (2026-10-20 20:55 ET) — E4 definition fixed before any E4 computation
- E4a (from the existing E2/E3 rows, no new run): for each team-month, its SHARE of the bill (charge / bill) under R2, R4,
  R5 at AUTO_SUSPEND 60, 300, 600. Metric: median absolute change in share 60->600, per rule. Bill shifts only.
- E4b (new run, run_e4.py, AUTO_SUSPEND 60 and 600, exact rules only): for each instance-month and each team i in turn,
  "double" team i by adding a copy of each of its queries starting when the original ends (same duration; doubles its busy
  time). Re-allocate. Metric (monotonicity): share of (instance-month, i, other team j) cases where j's charge RISES because i
  doubled, per rule R2, R4, R5; also the median rise when it happens (% of j's charge).
- Expectation stated before computing: R5 never raises another team's charge (in the coverage game an added interval can
  only shrink others' per-second shares or leave them unchanged); R2/R4 may.

## Pre-registered experiments (freeze before running; change only with a dated note)
- E1 Reconciliation (Snowflake): does the billing model reproduce metered credits? Metric: |model - metered| / metered per hour and overall.
  Allocation rules must sum to the metered invoice exactly (after a documented residual step).
- E2 Unattributed share (Redset): fraction of billed seconds outside any query's execution (idle + tails + minimums),
  per instance; distribution across instances, by serverless/provisioned.
- E3 Rule comparison (Redset + Snowflake): native-style execution-only attribution + proportional residual, equal split,
  marginal (leave-one-out), Shapley (sweep). Metrics:
  (a) core violations: share of teams/coalitions charged above standalone cost;
  (b) overcharge vs Shapley; (c) month-to-month volatility of each team's charge with its own usage held fixed;
  (d) compute time per instance-month.
- E4 What-if: change in each team's charge when AUTO_SUSPEND changes (60/300/600 s) or a team's workload doubles.
  Bill shifts only -- no leave/stay analysis.
- Primary claims allowed only if they hold on Redset AND match the direction on the Snowflake run.

## Schedule
- Wk1 Oct 20–26: data on disk; Redset loader; engine (4 rules + min-bill extension); write proof; freeze this plan.
- Wk2 Oct 27–Nov 2: E1 Snowflake run (after credit check); E2–E4 on Redset.
- Wk3 Nov 3–9: results, figures.
- Wk4 Nov 10–16: full draft.
- Wk5 Nov 17–24: independent fact-check; co-authors final; submit Nov 24.

## Deviation 2 (2026-10-22 08:40 ET, found in the independent number check after all results) — disclose in the paper
- Runner cut calendar months with DuckDB strftime(to_timestamp(s)), which uses the session time zone (US Eastern).
  Redset starts 2024-03-01 00:00 UTC, so its first ~5 h fell into a "2024-02" stub month: 56 instance-months per setting
  with a median billed time of 5.2 h (vs ~600 h for full months). The frozen definition says Mar–May calendar months.
- Fix: drop the 2024-02 stub rows (no re-run; rows are independent). Reported numbers use 264 instance-months, 1,414
  team-months, 25,856 coalitions and 7,096 bystander cases per setting. Results with the stub kept are reported as a
  sensitivity line. Effect: every headline moves by < 3 points EXCEPT month-to-month volatility, where the stub had
  excluded most teams (29 vs 117 eligible); without it Shapley is the steadiest rule (CV 3.8–4.5% vs 5.6–5.9%
  proportional, 9.0–26.6% marginal). Both versions are reported; the earlier "negative result" is withdrawn.
- Also from the check: medians now use the standard (midpoint) median; live-run charges are scaled to the metered
  compute invoice (0.953 and 1.426 credits) instead of the modelled one; engine timing re-measured with
  verify/bench_engine.py (1M queries, 10 teams: sweep 0.2–0.6 s, all rules 6.7–7.3 s, one core).

## Independent review (2026-10-22 09:30 ET) — changes in draft 3
- SQL listing rewritten as a prefix-sum sweep (old range join was O(islands x segments): 107 s per 1M queries at a=60).
  New listing = sql/coverage_shapley.sql; matches sweep/brute force to 1e-12 s; 1M queries 0.83 s (a=600) / 1.08 s (a=60), 1 core.
- R4's P3 failure attributed to rescaling (raw marginals can only fall). Prop. below-minimum example made non-degenerate.
- Corrected: 87.7% (not 87.6%); "within 1.2%" of event-recorded running time; tail deciles with standard median
  (7.5/12.5/16.3 low; 6.8/10.9/8.4 high); named-team-only P2 rates added; R2 passes the doubling test by construction (stated);
  stability claim softened; Databricks auto-stop minimums corrected; rais24 authors corrected; keywords/CCS added.

## Addendum 4 (2026-10-22 17:10 ET) — E5 and E6 fixed before either is run
- E5 isolated growth (run_e5.py, Redset, same eligible instances and 1% pooling as E2/E3, AUTO_SUSPEND 60 and 600):
  for each instance-month and each named team i, add 10 one-second queries for team i at uniform random times within the
  month's observed span [min s, max e] (Python random.Random seeded with "key|month|i"). Re-allocate. Metric: share of
  (instance-month, i, other named team j) cases where j's charge RISES, per rule R2, R4, R5; median rise when it does.
  Months labelled 2024-02 (the 5-hour stub, Deviation 2) are dropped in the analysis, as for every other result.
  Expectation stated before running: R5 never rises (Prop. bystander); R2 rises in many cases (each isolated query adds up
  to a + 60 s of bill but 1 s of execution); R4 in some.
- E6 SQL on Snowflake (sf/sf_sql_check.py): run the paper's chargeback listing inside Snowflake (warehouse CB_SHARED, XS)
  over QUERY_HISTORY of the E1 run (team = query tag, interval = [end - execution_time, end], a = 60 and 300), and compare
  each team's charge with the Python sweep on the same intervals. Then time the listing on a 1,000,000-row synthetic table
  (GENERATOR; 10 teams; one month; exponential 5 s run times; a = 60 and 600) on the XS warehouse. Metrics: max abs
  difference (s); elapsed time. If Snowflake rejects any syntax, record the error and the minimal change, and report it.
  Budget < 0.1 credits.

## E5 / E6 results (2026-10-25; analysis by the pre-registered definitions, stub month dropped)
- E5 isolated growth: R2 raises a bystander in 67.9% (60 s) / 40.6% (600 s) of 7,096 cases; R4 50.2% / 26.2%; R5 0 / 0.
  Median rises 0.01–0.2%. With stub kept: R2 64.3/37.3, R4 47.8/24.4, R5 0. As expected before the run.
- E6 Snowflake (sf/runs/e6_1792702899.json): listing ran as printed; vs Python sweep max diff 2.3e-13 s (a=60), 5.7e-14 s
  (a=300); 1M synthetic rows on XS: 1.04 s (a=600), 3.48 s (a=60). No fallback needed.

## Addendum 5 (2026-10-26 21:10 ET) — E7 (assumption A1 sensitivity), fixed before it is run
- Question: A1 keeps each query's timing when other teams are removed; with less contention a team alone might run faster,
  lowering its standalone cost and possibly pushing charges above it.
- E7 (run_e7.py, Redset, same eligible instances, 1% pooling, months as E2/E3; stub month dropped in analysis;
  AUTO_SUSPEND 60 and 600): for every named team-month, recompute the team's standalone cost with every one of its
  execution intervals shortened by f in {10%, 20%, 30%} (start kept, end moved earlier). Compare with each rule's charge
  computed on the full warehouse at original timing (R2, R3, R4, R5). Metric: share of named team-months charged above the
  shortened standalone cost, per rule and f. Expectation stated before running: R5 stays at or near 0 for 10%, because the
  shortened standalone cost loses at most f x the team's busy time while tails are unchanged; R2/R3 rise slightly.

## E7 result (2026-10-26 22:10 ET) — expectation NOT met; reported as such
- Named team-months charged above the shortened standalone cost (stub dropped), f = 10 / 20 / 30%:
  60 s: R5 8.5 / 12.3 / 14.4%; R2 21.1 / 22.4 / 24.3; R3 40.4 / 41.8 / 43.4; R4 13.9 / 16.3 / 18.9.
  600 s: R5 3.1 / 4.0 / 4.6%; R2 15.4 / 16.2 / 16.8; R3 29.1 / 29.2 / 29.4; R4 8.8 / 10.0 / 11.8.
- R5 excess at 10%: median 2.1% (60 s) / 0.4% (600 s), p90 8.1 / 3.6%. ~2/3 of violators had <1% slack at observed timing.
- Stated expectation ("R5 at or near 0 at 10%") was wrong; the paper says so.

## Addendum 6 (2026-10-27 21:25 ET, before it is run) — the pre-registered no-compile sensitivity, not run until now
- The frozen definitions list "Sensitivity: without compile"; it was never run and the paper did not report it (found in
  an external review of the plan against the paper). Run now exactly as defined: interval end = arrival + queue +
  execution (compile_s subtracted); everything else unchanged (eligibility, 1% team rule recomputed on the shorter
  intervals, months, rules). Settings 60/300/600 s. run_e2e3.py --no-compile -> results/e2e3_nocompile.jsonl;
  analysis/nocompile.py prints main vs no-compile side by side.
- Expectation: the unassigned share rises slightly (less attributed time); the ordering of the rules and Shapley's zero
  standalone violations are unchanged (the theorem does not depend on how intervals are measured). Reported either way,
  in one sentence in the sensitivity section.
