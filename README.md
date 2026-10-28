# Who Pays for Idle? — artifacts

Code, raw results, Snowflake logs and the pre-registration for the paper
*Who Pays for Idle? Fair Chargeback for Shared Cloud Data Warehouses*.

A shared warehouse is billed per second while it runs, including idle tails after each query. The paper models the bill
as a cost-sharing game, shows that when the auto-suspend timeout is at least 60 s the Shapley split is exact in one sweep
(each billed second divided equally among the teams keeping the warehouse up), and compares it with common chargeback
rules on 94 shared Redshift instances from Redset replayed under per-second billing, and on a live Snowflake warehouse.

## What is here

| Path | Contents |
|---|---|
| `PREREGISTRATION.md` | Study plan with dated addenda, deviations and results notes, as written during the work |
| `PROOF_NOTES.md` | Working notes for the coverage-game proof |
| `common/billing.py` | Billing model (running periods, 60 s minimum) and the Shapley sweep |
| `chargeback/engine.py` | The five rules R1–R5 compared in the paper |
| `chargeback/sql/coverage_shapley.sql` | The chargeback SQL printed in the paper (window functions only) |
| `chargeback/redset_load.py`, `eligibility.py` | Redset to per-instance intervals; instance inclusion rule |
| `chargeback/run_e2e3.py`, `run_e4.py`, `run_e5.py`, `run_e7.py` | Replays (E2–E5, E7) |
| `chargeback/results/` | Raw result files `e2e3.jsonl`, `e4b.jsonl`, `e5.jsonl`, `e7.jsonl` |
| `data/redset_iv/` | Instance inventory and eligibility (the interval files themselves are rebuilt by `get_data.sh`) |
| `chargeback/sf_e1.py`, `sf/` | Snowflake: the four-team live run (E1), the SQL check inside Snowflake (E6), raw logs (`sf/runs/`), Snowflake's own records for the run's warehouse (`sf/truth/`) |
| `analysis/` | Scripts that print every number in the paper from the result files |
| `paper/` | LaTeX source, figures and `make_figs.py` |
| `tests/` | Billing model, sweep vs brute-force Shapley, engine, and the SQL vs Python |

## Reproduce the paper's numbers (minutes, no download)

```
pip install -r requirements.txt
python3 tests/test_billing.py && python3 tests/test_engine.py && python3 tests/test_sql.py
./run.sh analysis
```

`./run.sh analysis` runs the pre-registered E2/E3 and E4b analyses, `analysis/verify_sigmod.py` (an independent
recomputation of every reported fleet number, with the stub month dropped as in Deviation 2), the exploratory analyses
(`explore_sigmod.py`, marked exploratory in the paper), E5 and E7 (`e5_e7.py`), the sampled-Shapley accuracy check below
the 60 s minimum, the 1M-query timing benchmark, the E1 billing validation against Snowflake's records, and every figure.

## Re-run the replays (hours)

```
./get_data.sh            # Redset (several GB) -> data/redset_iv
./run.sh e2e3            # also e4, e5, e7
```

## Snowflake runs

E1 and E6 used a personal Snowflake trial account and one dedicated X-Small warehouse (`CB_SHARED`). Credentials are read
from `~/.snowflake/connections.toml`; none are stored here. Timings on another account will differ; our raw logs and
Snowflake's own records are in `sf/runs/` and `sf/truth/`.

## Data

Redset: van Renen et al., *Why TPC Is Not Enough: An Analysis of the Amazon Redshift Fleet*, VLDB 2024 (CC BY-NC 4.0).

## License

MIT (code). Redset is distributed by Amazon under its own license.
