#!/usr/bin/env bash
# Crucible LLM benchmark runner — see README.md in this directory.
#
# The Crucible binary and the target endpoint are NOT vendor-committed:
#   CRUCIBLE_BIN       path to the crucible-llm binary (default: crucible-llm on PATH)
#   CRUCIBLE_URL       OpenAI-compatible /v1 endpoint under test (default: localhost)
#   CRUCIBLE_TIMEOUT   connection/idle-read timeout in seconds (default: Crucible's own, 120)
#   CRUCIBLE_TOKENIZER path to the served model's HF tokenizer.json, so C1's haystack is sized in
#                      real tokens (default: absent -> Crucible's chars/4 estimate, flagged
#                      `estimated`, and the nominal "128k" tests far fewer real tokens)
#   CRUCIBLE_POLL      seconds between live-stage lines on stderr (default: 30)
#
# A `run` prints its live stage: the current engine and every C1 cell, with elapsed seconds since
# the pass started, by polling the newest Crucible log under ~/.local/share/crucible/logs.
# (C1 alone is ~36 min with the real tokenizer, so silence for that long is not informative.)
#
# Engines: this suite records C1, C2, C3 (capability); --no-hardware drops Engine D (see README).
# All three run against one endpoint in a single pass. Name engines explicitly to run a subset.
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
TOKENIZER="${CRUCIBLE_TOKENIZER:-}"
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
    if [ -n "$TOKENIZER" ]; then args+=(--tokenizer "$TOKENIZER"); fi
    # Engine set: C1, C2, C3 (capability). With no engine args, select this set explicitly
    # (Crucible's own default also pulls in the timing and concurrency engines). All three run
    # against one endpoint; name engines to run a subset.
    if [ "$#" -eq 0 ]; then set -- niah reasoning structured; fi
    for e in "$@"; do args+=(--engine "$e"); done
    echo "Run: $model  URL: $URL  Date: $(date +%F)"
    # Capability verdicts (C1/C2/C3) print to stderr — tee to run.log.
    "$BIN" "${args[@]}" 2> >(tee "$out/run.log" >&2) &
    binpid=$!
    # Live stage: poll the newest Crucible log for engine transitions and C1 cells.
    LOGDIR="${XDG_DATA_HOME:-$HOME/.local/share}/crucible/logs"
    poll="${CRUCIBLE_POLL:-30}"
    start=$(date +%s)
    last=""
    while kill -0 "$binpid" 2>/dev/null; do
      sleep "$poll" 2>/dev/null || true
      kill -0 "$binpid" 2>/dev/null || break
      log="$(ls -t "$LOGDIR"/run-*.log 2>/dev/null | head -1 || true)"
      [ -n "${log:-}" ] || continue
      # Ignore another run's log if one is being written concurrently.
      grep -qaF "model=$model" "$log" 2>/dev/null || continue
      stage="$(grep -aE 'Engine C[0-9]|C1:[0-9]+k-d[0-9]+' "$log" 2>/dev/null | tail -1 | cut -c16-200 || true)"
      [ -n "$stage" ] || continue
      [ "$stage" = "$last" ] && continue
      last="$stage"
      printf '  t+%ss | %s\n' "$(( $(date +%s) - start ))" "$stage"
    done
    rc=0; wait "$binpid" || rc=$?
    [ "$rc" -eq 0 ] || echo "crucible-llm exited $rc" >&2
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
    echo "  CRUCIBLE_TOKENIZER (optional, path to the served model's tokenizer.json)"
    echo "  CRUCIBLE_POLL (optional, seconds between live-stage lines; default 30)"
    ;;
esac
