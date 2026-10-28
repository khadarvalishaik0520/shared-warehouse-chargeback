#!/bin/bash
# ./run.sh analysis   every number, table and figure in the paper from the committed result files (minutes, no download)
# ./run.sh e2e3|e4|e5|e7|e2e3nc   re-run one replay on Redset (needs data/redset_iv from ./get_data.sh; hours)
set -eu; cd "$(dirname "$0")"
case "${1:-}" in
  analysis)
    python3 chargeback/analyze_e2e3.py chargeback/results/e2e3.jsonl
    python3 chargeback/analyze_e4b.py chargeback/results/e4b.jsonl
    python3 analysis/verify_sigmod.py chargeback/results --drop-feb
    python3 analysis/explore_sigmod.py
    python3 analysis/e5_e7.py chargeback/results
    python3 analysis/nocompile.py chargeback/results
    python3 analysis/sampled_accuracy.py
    python3 analysis/bench_engine.py
    python3 sf/validate_billing.py sf/truth sf/runs/e1_1792522545.jsonl CB_SHARED auto
    (cd paper && python3 make_figs.py) ;;
  e2e3|e4|e5|e7) python3 -u chargeback/run_${1}.py data/redset_iv chargeback/results ;;
  e2e3nc) python3 -u chargeback/run_e2e3.py data/redset_iv chargeback/results --no-compile ;;
  *) sed -n 2,3p "$0" ;;
esac
