-- Coverage-Shapley chargeback (Theorem 1), valid when auto_suspend >= 60 s. Identical to the paper's listing.
-- Input: queries(team, s, e) in epoch seconds, one warehouse and billing period; $a = auto_suspend seconds.
WITH iv AS (SELECT team, s, e + $a AS e FROM queries),
ord AS (SELECT team, s, e, MAX(e) OVER (PARTITION BY team
          ORDER BY s, e ROWS BETWEEN UNBOUNDED PRECEDING
          AND CURRENT ROW) AS cm FROM iv),
isl AS (SELECT team, s, e, CASE WHEN s <= LAG(cm) OVER (PARTITION
          BY team ORDER BY s, e) THEN 0 ELSE 1 END AS new FROM ord),
grp AS (SELECT team, s, e, SUM(new) OVER (PARTITION BY team ORDER
          BY s, e ROWS UNBOUNDED PRECEDING) AS k FROM isl),
cover AS (SELECT team, MIN(s) s, MAX(e) e FROM grp GROUP BY team, k),
ev AS (SELECT t, SUM(d) d FROM (SELECT s t, 1 d FROM cover UNION ALL
          SELECT e, -1 FROM cover) x GROUP BY t),
cnt AS (SELECT t, SUM(d) OVER (ORDER BY t ROWS UNBOUNDED PRECEDING)
          n, LEAD(t) OVER (ORDER BY t) t2 FROM ev),
w AS (SELECT t, CASE WHEN n > 0 THEN (t2 - t) / n ELSE 0 END x
          FROM cnt),
g AS (SELECT t, SUM(x) OVER (ORDER BY t ROWS UNBOUNDED PRECEDING)
          - x AS g FROM w)
SELECT c.team, SUM(ge.g - gs.g) AS charge_s FROM cover c
  JOIN g gs ON gs.t = c.s JOIN g ge ON ge.t = c.e GROUP BY c.team;
