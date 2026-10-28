# Chargeback cost game — proof notes (draft 2026-10-19; to be checked by an independent reviewer before it goes in the paper)

## Setup
Fixed-size warehouse, auto-suspend a seconds, resume minimum m = 60 s. Query q runs on [s_q, e_q]; team(q) in N.
For a coalition S of teams, c(S) = billed seconds if only S's queries ran, with the same timing.
Assumption A1 (timing invariance): removing other teams' queries does not change S's query timings (no queueing/speed effects).
Assumption A2: the warehouse suspends exactly a seconds after its last query ends.

## Lemma 1 (running periods = components)
Let R(S) = union over S's queries of [s_q, e_q + a]. The warehouse's running periods under S are exactly the connected
components of R(S). Proof: a period starts at the first query start; a later query with s <= (current last end) + a
starts inside the current component and extends it; one with s > (last end) + a starts a new component and the
previous period ends at (last end) + a. Hence c(S) = sum over components C of R(S) of max(m, |C|).

## Theorem 1 (a >= m: coverage game)
If a >= m, every component has length >= a >= m, so c(S) = |R(S)| = |union_{i in S} A_i| with A_i = R({i}).
Hence c is a coverage (union-measure) function: submodular, monotone, c(empty)=0.
(i) Shapley: phi_i = integral over A_i of 1/|N(x)| dx, N(x) = {teams whose A_j contains x}.
    Proof: for fixed x the game S -> 1[S intersects N(x)] gives each member of N(x) 1/|N(x)| by symmetry and null-player;
    Shapley is linear, and c(S) is the integral of these games over x.
(ii) Core: a submodular cost game is concave; its core is non-empty and contains the Shapley value (Shapley 1971).
     So no coalition of teams is charged more than its standalone bill.
(iii) Computation: a sweep over the 2|components| endpoints of all A_i, O(M log M) for M queries.
Empirical check (tests/test_billing.py): sweep equals brute-force Shapley to 3e-13 s on 1,600 random instances; 0 core violations.

## Where it breaks (must be measured or extended, not hidden)
- Snowflake allows AUTO_SUSPEND of any integer >= 0 (0/NULL = never suspend; default 600 s). Its suspend process runs
  about every 30 s, so A2 holds only up to a ~0–30 s extra tail -> E1 measures the real tail on Snowflake.
- 30 <= a < 60 (or any a < m): short components are billed m, c(S) = |R(S)| + sum_C max(0, m - |C|);
  the second term is not a coverage function and the sweep is wrong (up to ~170 s on test instances).
  Plan: exact Shapley per connected component of the grand coalition when its team count is small; permutation sampling
  with a confidence bound otherwise. Report how often this case occurs.
- A1 fails when teams contend (queueing). E1 quantifies on Snowflake; Redset queue times give a bound.
- Not covered: multi-cluster warehouses, resizing mid-period, cloud-services credits.

## Related (cite)
Shapley (1953); Shapley (1971) cores of convex games; coverage / union games; McLean & Sharkey 1998 (Shapley for a shared
computer center's queues); Upadhyaya, Balazinska, Suciu PVLDB 2012; Kesidis, Walrand et al. IEEE/ACM ToN.
Need to check: whether "Shapley of a union-of-intervals game = 1/k per point" is already published in a scheduling/
cost-sharing context (likely yes, e.g. airport/infrastructure games) -> cite it; our contribution is the reduction from
warehouse billing rules, not the coverage identity.
