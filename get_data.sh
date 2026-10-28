#!/bin/bash
# Downloads Redset (Amazon Redshift fleet trace, CC BY-NC 4.0; serverless + provisioned parts) into data/redset and
# builds the per-instance query intervals in data/redset_iv. Only needed to re-run the replays (./run.sh e2e3 ...).
set -eu; cd "$(dirname "$0")"; mkdir -p data/redset data/redset_iv; cd data/redset
S3="https://redshift-downloads.s3.amazonaws.com"
list_s3() { local tok=""; while :; do
    x=$(curl -sS "$S3/?list-type=2&prefix=$1${tok:+&continuation-token=$tok}")
    echo "$x" | tr '<' '\n' | awk -F'>' '/^Key>/{print $2}'
    tok=$(echo "$x" | tr '<' '\n' | awk -F'>' '/^NextContinuationToken>/{print $2}' | sed 's/+/%2B/g;s/\//%2F/g;s/=/%3D/g')
    [ -z "$tok" ] && break; done; }
curl -sS -O "$S3/redset/LICENSE"; curl -sS -O "$S3/redset/README"
list_s3 "redset/" | grep '/parts/.*\.parquet$' | while read k; do
  out="${k#redset/}"; mkdir -p "$(dirname "$out")"; [ -s "$out.ok" ] && continue
  curl -sS -C - -o "$out" "$S3/$k" && touch "$out.ok" && echo "got $out"; done
cd ../..; mv data/redset_iv/inventory.jsonl data/redset_iv/inventory.committed.jsonl 2>/dev/null || true; touch data/redset_iv/inventory.jsonl
python3 -u chargeback/redset_load.py data/redset data/redset_iv && python3 chargeback/eligibility.py data/redset_iv
