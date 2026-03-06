#!/usr/bin/env bash
# OmniBoard — Setup Script for macOS (M1/M2/M3)
# Run once after cloning: bash setup.sh

set -e
BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RESET='\033[0m'

step() { echo -e "\n${BOLD}→ $1${RESET}"; }
ok()   { echo -e "${GREEN}✓ $1${RESET}"; }
warn() { echo -e "${YELLOW}⚠ $1${RESET}"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

step "Checking prerequisites"

# Node.js
if ! command -v node &>/dev/null; then
  echo "Node.js not found. Installing via Homebrew..."
  if ! command -v brew &>/dev/null; then
    echo "Homebrew not found. Install from https://brew.sh first."
    exit 1
  fi
  brew install node
fi
ok "Node.js $(node --version)"

# Python (for Trigger.dev automations)
if ! command -v python3 &>/dev/null; then
  warn "Python 3 not found. Trigger.dev automations won't work. Install from https://python.org"
else
  ok "Python $(python3 --version)"
fi

# UV (Python package manager for automations)
if ! command -v uv &>/dev/null; then
  warn "uv not found. Installing..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.cargo/bin:$PATH"
fi

step "Installing API server dependencies"
cd "$SCRIPT_DIR/server"
npm install
ok "Server deps installed"

step "Initialising SQLite database"
npm run db:push
ok "omniboard.db created"

step "Installing React app dependencies"
cd "$SCRIPT_DIR/app"
npm install
ok "App deps installed"

step "Installing Python automation dependencies (optional)"
cd "$SCRIPT_DIR"
if command -v uv &>/dev/null; then
  uv pip install -r requirements.txt 2>/dev/null && ok "Python deps installed" || warn "Python install failed — automations won't run"
else
  warn "Skipping Python deps (uv not available)"
fi

step "Creating .env file"
if [ ! -f "$SCRIPT_DIR/.env" ]; then
  cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
  ok ".env created from example. Edit it to add TRIGGER_SECRET_KEY and OPENROUTER_API_KEY."
else
  ok ".env already exists — skipped"
fi

echo ""
echo -e "${BOLD}${GREEN}Setup complete!${RESET}"
echo ""
echo "Start the app with:"
echo ""
echo "  Terminal 1 (API server):"
echo "    cd server && npm run dev"
echo ""
echo "  Terminal 2 (React app):"
echo "    cd app && npm run dev"
echo "    → http://localhost:5173"
echo ""
echo "  Terminal 3 (automations, optional):"
echo "    Edit .env → add TRIGGER_SECRET_KEY"
echo "    npm run dev"
echo ""
