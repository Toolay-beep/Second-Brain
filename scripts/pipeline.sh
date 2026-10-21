#!/usr/bin/env bash
# Deterministic delivery gate (see notes/06-deterministic-delivery-pipelines.md).
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONHASHSEED=0 LC_ALL=C TZ=UTC

echo "== 1. manifest verify (inputs match committed manifest)"
python3 -m agentkit.manifest verify .

echo "== 2. unit tests"
python3 -m unittest discover -s tests -t . -q

echo "== 3. determinism: two manifest builds must be byte-identical"
a=$(python3 -m agentkit.manifest build . -o - | sha256sum)
b=$(python3 -m agentkit.manifest build . -o - | sha256sum)
[ "$a" = "$b" ] || { echo "non-deterministic manifest"; exit 1; }

echo "== provenance: root_digest=$(python3 -c 'import json;print(json.load(open("agent-manifest.json"))["root_digest"])')"
