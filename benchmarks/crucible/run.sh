#!/usr/bin/env bash
# Crucible LLM benchmark runner — see README.md in this directory.
#
# The Crucible binary and the target endpoint are NOT vendor-committed:
#   CRUCIBLE_BIN       path to the crucible-llm binary (default: crucible-llm on PATH)
#   CRUCIBLE_URL       OpenAI-compatible /v1 endpoint under test (default: localhost)
#   CRUCIBLE_CTX       served context size of the model under test; REQUIRED for a `run` unless
#                      CRUCIBLE_NIAH_CONTEXTS is set. Used to trim the C1 ladder.
#   CRUCIBLE_NIAH_MAX_TOKENS  C1 per-cell generation budget (default: 2048); the trim uses this value.
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

# C1 (NIAH) ladder pinned by this suite (see README -> Protocol deviations): 8 context sizes
# x 5 depths = 40 cells max, trimmed per run to the model's served context.
NIAH_LADDER_TOKENS="16000 32000 64000 128000 160000 192000 256000 512000"
NIAH_DEPTHS="0,25,50,75,100"
NIAH_BUDGET="${CRUCIBLE_NIAH_MAX_TOKENS:-2048}"

# Model ids are bare; sanitize path separators so a 'provider/model' id stays one dir.
sanitize() { printf '%s' "$1" | tr '/:' '__'; }

# 16000 -> "16k"; a token count that is not a multiple of 1000 is emitted as the raw number.
niah_label() { if [ $(( $1 % 1000 )) -eq 0 ]; then printf '%dk' "$(( $1 / 1000 ))"; else printf '%d' "$1"; fi; }

# Emit a comma-separated CSV of ladder labels whose token size fits `ctx`
# (value + budget <= ctx), ascending, with no trailing comma. Empty when none fit.
niah_csv() {
  local ctx="$1" csv="" t label
  for t in $NIAH_LADDER_TOKENS; do
    [ $(( t + NIAH_BUDGET )) -le "$ctx" ] || continue
    label="$(niah_label "$t")"
    if [ -z "$csv" ]; then csv="$label"; else csv="$csv,$label"; fi
  done
  printf '%s' "$csv"
}

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
    # C1 ladder: trim the pinned sizes to the served context unless Crucible's own env
    # override is set (then pass no ladder flags and let Crucible read its env itself).
    c1_ctx="${CRUCIBLE_CTX:-}"
    c1_ladder="env"
    for e in "$@"; do
      [ "$e" = niah ] || continue
      [ -z "${CRUCIBLE_NIAH_CONTEXTS:-}" ] || break
      if [ -z "$c1_ctx" ]; then
        echo "CRUCIBLE_CTX (served context size) is required to trim the C1 ladder" >&2
        exit 1
      fi
      c1_ladder="$(niah_csv "$c1_ctx")"
      if [ -z "$c1_ladder" ]; then
        echo "no C1 ladder size fits ctx $c1_ctx" >&2
        exit 1
      fi
      args+=(--niah-contexts "$c1_ladder" --niah-depths "$NIAH_DEPTHS")
      break
    done
    for e in "$@"; do args+=(--engine "$e"); done
    echo "Run: $model  URL: $URL  Date: $(date +%F)  C1 ctx: ${c1_ctx:-env}  ladder: $c1_ladder"
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
    echo "  CRUCIBLE_CTX (served context size; required to trim the C1 ladder unless CRUCIBLE_NIAH_CONTEXTS is set)"
    echo "  CRUCIBLE_NIAH_MAX_TOKENS (C1 per-cell generation budget; default 2048)"
    echo "  CRUCIBLE_TIMEOUT (optional, seconds)"
    echo "  CRUCIBLE_TOKENIZER (optional, path to the served model's tokenizer.json)"
    echo "  CRUCIBLE_POLL (optional, seconds between live-stage lines; default 30)"
    ;;
esac
