#!/usr/bin/env bash
# Start the full local dev stack in a tmux session.
#
# Layout (single window, 2x2 grid):
#   ┌──────────────────────┬──────────────────────┐
#   │  postgres-tunnel     │  redis-tunnel        │
#   ├──────────────────────┼──────────────────────┤
#   │  run-staging (API)   │  web-dev (Vite)      │
#   └──────────────────────┴──────────────────────┘
#
# The API pane waits for both tunnels to be reachable before starting uvicorn.
#
# Usage:
#   scripts/dev-stack.sh           # start (or attach if already running)
#   scripts/dev-stack.sh stop      # kill the session
#   scripts/dev-stack.sh status    # show whether the session is running

set -euo pipefail

SESSION="trigpointing-dev"
REPO_ROOT="$(git rev-parse --show-toplevel)"

cmd_status() {
  if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "✅ Session '$SESSION' is running. Attach with: tmux attach -t $SESSION"
  else
    echo "⏸  Session '$SESSION' is not running."
  fi
}

cmd_stop() {
  if tmux has-session -t "$SESSION" 2>/dev/null; then
    tmux kill-session -t "$SESSION"
    echo "🛑 Killed session '$SESSION'."
  else
    echo "Nothing to stop — session '$SESSION' isn't running."
  fi
}

cmd_start() {
  command -v tmux >/dev/null 2>&1 || { echo "❌ tmux not installed. sudo apt install tmux"; exit 1; }

  if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "Session '$SESSION' already exists. Attaching."
    exec tmux attach -t "$SESSION"
  fi

  # Wait commands kept as plain strings so they survive the quoting through tmux.
  local wait_for_stack='echo "⏳ waiting for postgres + redis tunnels..."; until pg_isready -h localhost -p 5433 >/dev/null 2>&1 && (echo > /dev/tcp/localhost/6379) 2>/dev/null; do sleep 1; done; echo "✅ tunnels up";'

  # Pane 0 (top-left): postgres tunnel
  tmux new-session -d -s "$SESSION" -n stack -c "$REPO_ROOT" \
    'echo "🐘 postgres-tunnel"; make postgres-tunnel; echo "— exited; press any key to close —"; read -n1'

  # Pane 1 (right): redis tunnel
  tmux split-window -h -t "$SESSION":0.0 -c "$REPO_ROOT" \
    'echo "🟥 redis-tunnel"; make redis-tunnel; echo "— exited; press any key to close —"; read -n1'

  # Pane 2 (bottom-left): API, waiting for both tunnels
  tmux split-window -v -t "$SESSION":0.0 -c "$REPO_ROOT" \
    "${wait_for_stack} echo '🚀 starting FastAPI'; make run-staging; echo '— exited; press any key to close —'; read -n1"

  # Pane 3 (bottom-right): web-dev (Vite)
  tmux split-window -v -t "$SESSION":0.1 -c "$REPO_ROOT" \
    'echo "⚛️  web-dev (Vite)"; make web-dev; echo "— exited; press any key to close —"; read -n1'

  # Even out the 2x2 grid
  tmux select-layout -t "$SESSION":0 tiled

  echo "✅ Started session '$SESSION'."
  echo "   Attach:  tmux attach -t $SESSION   (or: make dev-stack-attach)"
  echo "   Stop:    scripts/dev-stack.sh stop (or: make dev-stack-stop)"
  echo "   Status:  scripts/dev-stack.sh status"
}

case "${1:-start}" in
  start)  cmd_start ;;
  stop)   cmd_stop ;;
  status) cmd_status ;;
  *)      echo "Usage: $0 [start|stop|status]"; exit 1 ;;
esac
