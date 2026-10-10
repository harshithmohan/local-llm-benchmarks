#!/usr/bin/env bash
# Crucible LLM benchmark runner — see README.md in this directory.
#
# The Crucible binary and the target endpoint are NOT vendor-committed:
#   CRUCIBLE_BIN     path to the crucible-llm binary (default: crucible-llm on PATH)
#   CRUCIBLE_URL     OpenAI-compatible /v1 endpoint under test (default: localhost)
#   CRUCIBLE_TIMEOUT connection/idle-read timeout in seconds (default: Crucible's own, 120)
#
# Engines: this suite records C1, C2, C3 (capability); --no-hardware drops Engine D (see README).
# C1/C3 need a server started with --reasoning off and C2 needs the model's default, so the set is
# normally measured in two passes with explicit engine names - the no-engine default below runs
# all three against whatever endpoint you point it at.
#
# NOTE: Crucible's --export file carries only stream metrics (from its timing engines), and
# this suite runs none of them, so the export is not used. The capability verdicts (C1/C2/C3)
# print to stderr, which is teed to run.log.
#
# usage:
#   ./run.sh run <model-id> [engine ...]   headless run; run.log under results/<model-id>/
#   ./run.sh cleanup <model-id> [card-stem]  remove results/<model-id>/ (score must be recorded)
set -euo pipefail

BIN="${CRUCIBLE_BIN:-crucible-llm}"
URL="${CRUCIBLE_URL:-http://localhost:8080/v1}"
TIMEOUT="${CRUCIBLE_TIMEOUT:-}"
DIR="$(cd "$(dirname "$0")" && pwd)"

# Model ids are bare; sanitize path separators so a 'provider/model' id stays one dir.
sanitize() { printf '%s' "$1" | tr '/:' '__'; }

cmd="${1:-help}"
case "$cmd" in
  run)
    model="${2:?model id required, e.g. qwen36-35b-iq4xs}"
    shift 2
    name="$(sanitize "$model")"
    out="$DIR/results/$name"
    mkdir -p "$out"
    args=(--headless --url "$URL" --model "$model" --no-hardware)
    if [ -n "$TIMEOUT" ]; then args+=(--timeout "$TIMEOUT"); fi
    # Engine set: C1, C2, C3 (capability). With no engine args, select this set explicitly
    # (Crucible's own default also pulls in the timing and concurrency engines). C1/C3 require a
    # --reasoning off server and C2 the model's default - normally two passes, named explicitly.
    if [ "$#" -eq 0 ]; then set -- niah reasoning structured; fi
    for e in "$@"; do args+=(--engine "$e"); done
    echo "Run: $model  URL: $URL  Date: $(date +%F)"
    # Capability verdicts (C1/C2/C3) print to stderr — tee to run.log.
    "$BIN" "${args[@]}" 2> >(tee "$out/run.log" >&2)
    echo
    echo "Run log (capability verdicts): results/$name/run.log"
    echo "Next: record the result in scorecards/$name.md, then ./run.sh cleanup $model"
    ;;

  cleanup)
    model="${2:?model id required (safety: score must already be recorded)}"
    card="${3:-$model}"   # scorecard file stem; a card is per model, while the run id carries the quant
    name="$(sanitize "$model")"
    stem="$(sanitize "$card")"
    case "$name" in ..*|*/..*|*../*) echo "invalid name '$name'"; exit 1;; esac
    case "$stem" in ..*|*/..*|*../*) echo "invalid card name '$stem'"; exit 1;; esac
    if [ ! -f "$DIR/scorecards/$stem.md" ]; then
      echo "no score at scorecards/$stem.md — record the result before deleting results/$name/"; exit 1
    fi
    rm -rf "$DIR/results/$name"
    echo "Removed results/$name/; results live in scorecards/."
    ;;

  *)
    echo "usage: $0 run <model-id> [engine ...]  (default engines: niah reasoning structured)"
    echo "       $0 cleanup <model-id> [card-stem]   (card-stem defaults to the model id)"
    echo "  CRUCIBLE_BIN (default: crucible-llm)  CRUCIBLE_URL (default: http://localhost:8080/v1)"
    echo "  CRUCIBLE_TIMEOUT (optional, seconds)"
    ;;
esac
