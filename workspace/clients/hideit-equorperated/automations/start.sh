#!/usr/bin/env bash
# OmniBoard — Start both server and app in parallel
# Usage: bash start.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Kill background jobs on Ctrl+C
trap "kill 0" EXIT

echo "Starting OmniBoard..."
echo "  API server → http://localhost:3001"
echo "  React app  → http://localhost:5173"
echo "  Press Ctrl+C to stop both"
echo ""

# Start API server
(cd "$SCRIPT_DIR/server" && npm run dev) &

# Wait briefly so the server is up before the app connects
sleep 2

# Start React app
(cd "$SCRIPT_DIR/app" && npm run dev) &

# Open browser after another second
sleep 1
open http://localhost:5173 2>/dev/null || true

wait
