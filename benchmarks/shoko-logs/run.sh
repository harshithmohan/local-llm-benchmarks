#!/usr/bin/env bash
# shoko-logs benchmark runner — see README.md in this directory.
#
# usage:
#   ./run.sh setup <discovery|api-summary|full-spec>   create the bench branch from base
#   ./run.sh eval <run-name>                          run gates, export patch to runs/<run-name>/
#   ./run.sh cleanup <run-name>                       delete the branch (patch must be exported)
set -euo pipefail

# Shoko-WebUI checkout (repo under test). Override with SHOKO_WEBUI_DIR, or edit here.
WEBUI="${SHOKO_WEBUI_DIR:-/path/to/Shoko-WebUI}"
BASE=a715a49c4feb1b9d32c21b6691f652b298632b14
BRANCH=bench/shoko-logs
DIR="$(cd "$(dirname "$0")" && pwd)"

cmd="${1:-help}"
case "$cmd" in
  setup)
    variant="${2:?variant required: discovery | api-summary | full-spec}"
    [ -f "$DIR/prompt-$variant.md" ] || { echo "unknown variant '$variant'"; exit 1; }
    cd "$WEBUI"
    [ -z "$(git status --porcelain)" ] || { echo "working tree not clean — commit or stash first"; exit 1; }
    if git rev-parse --verify -q "$BRANCH" >/dev/null; then
      echo "branch $BRANCH already exists — run '$0 cleanup' first"; exit 1
    fi
    git checkout -b "$BRANCH" "$BASE"
    echo
    echo "Branch $BRANCH created at $BASE."
    echo "Next: start opencode in $WEBUI and paste the prompt from"
    echo "  $DIR/prompt-$variant.md"
    echo "Then: $0 eval <run-name>"
    ;;

  eval)
    name="${2:?run name required, e.g. qwen38-27b-full-spec}"
    cd "$WEBUI"
    [ "$(git branch --show-current)" = "$BRANCH" ] || { echo "not on branch $BRANCH"; exit 1; }
    out="$DIR/runs/$name"
    mkdir -p "$out"
    echo "Run: $name  Date: $(date +%F)"
    status=0
    for step in tscheck lint build; do
      echo "--- pnpm $step ---"
      if pnpm "$step" >"$out/$step.log" 2>&1; then
        echo "$step: PASS" | tee -a "$out/gates.log"
      else
        echo "$step: FAIL (details in $out/$step.log)" | tee -a "$out/gates.log"
        status=1
      fi
    done
    git add -A
    git diff --cached "$BASE" >"$out/patch.diff"
    git reset -q
    git diff --stat "$BASE" >"$out/stat.txt"
    echo
    echo "Patch exported: $out/patch.diff ($(wc -l <"$out/patch.diff") lines)"
    [ "$status" -eq 0 ] || echo "One or more gates failed — export kept, review $out/gates.log"
    echo "Next: grade with rubric.md into $out/score.md, then: $0 cleanup $name"
    exit "$status"
    ;;

  cleanup)
    name="${2:?run name required (safety: score must already be recorded)}"
    case "$name" in ..*|*/..*|*../*) echo "invalid run name '$name'"; exit 1;; esac
    if ! git -C "$WEBUI" rev-parse --verify -q "$BRANCH" >/dev/null; then
      echo "branch $BRANCH does not exist — nothing to clean up"
      exit 0
    fi
    cd "$WEBUI"
    if [ -n "$(git status --porcelain)" ]; then
      # uncommitted bench changes exist -> they must already be exported + graded
      [ -f "$DIR/runs/$name/patch.diff" ] || {
        echo "no exported patch at runs/$name/patch.diff — run eval first, the branch is about to be deleted"; exit 1
      }
      [ -f "$DIR/runs/$name/score.md" ] || {
        echo "no score at runs/$name/score.md — record the score in scorecards/ first, the run dir is about to be deleted"; exit 1
      }
      echo "discarding the model's bench changes (patch + score already exported):"
      git status --short
      git checkout -- .
      git clean -fd
    else
      # clean tree: nothing on the branch to lose; score only needs to exist
      # in the run dir OR the persistent scorecards record
      model="${name%%/*}"
      if [ ! -f "$DIR/runs/$name/score.md" ] && [ ! -f "$DIR/scorecards/$model.md" ]; then
        echo "no score recorded (runs/$name/score.md or scorecards/$model.md missing) — grade before cleanup"; exit 1
      fi
    fi
    git checkout master
    git branch -D "$BRANCH"
    rm -rf "$DIR/runs/$name"
    echo "Branch $BRANCH deleted and runs/$name/ removed; results live in scorecards/."
    ;;

  *)
    echo "usage: $0 setup <discovery|api-summary|full-spec> | eval <run-name> | cleanup <run-name>"
    ;;
esac
