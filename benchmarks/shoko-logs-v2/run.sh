#!/usr/bin/env bash
# shoko-logs benchmark runner — see README.md in this directory.
#
# usage:
#   ./run.sh setup                        create the bench branch from base
#   ./run.sh eval <run-name> [stage]      export the stage's patch to runs/<run-name>/
#                                         (stage defaults to 0; gates are run by the grader)
#   ./run.sh cleanup <run-name>           delete the branch (patch must be exported)
set -euo pipefail

# Shoko-WebUI checkout (repo under test). Override with SHOKO_WEBUI_DIR, or edit here.
WEBUI="${SHOKO_WEBUI_DIR:-/path/to/Shoko-WebUI}"
BASE=a715a49c4feb1b9d32c21b6691f652b298632b14
BRANCH=bench/shoko-logs-v2
DIR="$(cd "$(dirname "$0")" && pwd)"

cmd="${1:-help}"
case "$cmd" in
  setup)
    cd "$WEBUI"
    [ -z "$(git status --porcelain)" ] || { echo "working tree not clean — commit or stash first"; exit 1; }
    if git rev-parse --verify -q "$BRANCH" >/dev/null; then
      echo "branch $BRANCH already exists — run '$0 cleanup' first"; exit 1
    fi
    git checkout -b "$BRANCH" "$BASE"
    echo
    echo "Branch $BRANCH created at $BASE."
    echo "Next: run the implementation headlessly from the common parent of the"
    echo "  Shoko-WebUI and ShokoServer checkouts:"
    echo "  cd <parent> && opencode run --standalone --auto --agent build -m <model> \"\$(cat $DIR/prompt.md)\""
    echo "Then: $0 eval <run-name>"
    ;;

  eval)
    name="${2:?run name required, e.g. qwen38-27b-w4a16}"
    stage="${3:-0}"
    case "$stage" in 0|1|2) ;; *) echo "stage must be 0, 1 or 2 (got '$stage')"; exit 1;; esac
    cd "$WEBUI"
    [ "$(git branch --show-current)" = "$BRANCH" ] || { echo "not on branch $BRANCH"; exit 1; }
    out="$DIR/runs/$name"
    mkdir -p "$out"
    # One trajectory per run dir: every stage writes its own suffixed patch, so a
    # later stage's eval can never clobber an earlier stage's export.
    echo "Run: $name  Stage: $stage  Date: $(date +%F)"
    git add -A
    git diff --cached "$BASE" >"$out/patch-s$stage.diff"
    git diff --cached --stat "$BASE" >"$out/stat-s$stage.txt"
    git reset -q
    echo
    echo "Patch exported: $out/patch-s$stage.diff ($(wc -l <"$out/patch-s$stage.diff") lines)"
    echo "Next: grade into $out/score-s$stage.md (the grader runs the gates), then: $0 cleanup $name"
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
      ls "$DIR/runs/$name"/patch-s*.diff >/dev/null 2>&1 || {
        echo "no exported patch at runs/$name/patch-s*.diff — run eval first, the branch is about to be deleted"; exit 1
      }
      ls "$DIR/runs/$name"/score-s*.md >/dev/null 2>&1 || {
        echo "no score at runs/$name/score-s*.md — record the score in scorecards/ first, the run dir is about to be deleted"; exit 1
      }
      echo "discarding the model's bench changes (patch + score already exported):"
      git status --short
      git checkout -- .
      git clean -fd
    else
      # clean tree: nothing on the branch to lose; score only needs to exist
      # in the run dir OR the persistent scorecards record
      model="${name%%/*}"
      if ! ls "$DIR/runs/$name"/score-s*.md >/dev/null 2>&1 && [ ! -f "$DIR/scorecards/$model.md" ]; then
        echo "no score recorded (runs/$name/score-s*.md or scorecards/$model.md missing) — grade before cleanup"; exit 1
      fi
    fi
    git checkout master
    git branch -D "$BRANCH"
    rm -rf "$DIR/runs/$name"
    echo "Branch $BRANCH deleted and runs/$name/ removed; results live in scorecards/."
    ;;

  *)
    echo "usage: $0 setup | eval <run-name> [stage] | cleanup <run-name>"
    ;;
esac
