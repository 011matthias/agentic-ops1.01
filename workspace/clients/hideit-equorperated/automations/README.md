# OmniBoard — HideItEquorperated

Multi-project Kanban app with built-in automation. Runs **100% locally** — no cloud accounts, no API keys required.

## Stack

| Layer | Tech |
|-------|------|
| Frontend | React 18 + Vite + Tailwind + dnd-kit |
| Backend API | Hono.js + Drizzle ORM + SQLite |
| Automations | node-cron (in-process) + Ollama (local LLM) |

## Quick Start

### One command (recommended)

```bash
bash start.sh
```

Opens both the API server and React app, then launches your browser at `http://localhost:5173`. Press `Ctrl+C` to stop everything.

### First-time setup

```bash
bash setup.sh   # installs Node (via Homebrew if missing), creates DB, installs all deps
bash start.sh
```

### Manual (two terminals)

```bash
# Terminal 1 — API server
cd server && npm install && npm run db:push && npm run dev

# Terminal 2 — React app
cd app && npm install && npm run dev
```

## Built-in Automation

All automations run inside the API server process — no external scheduler needed.

| ID | Task | Trigger | What it does |
|----|------|---------|--------------|
| A1 | Deadline Scanner | Hourly (`:00`) | macOS notification for cards due within 24h or overdue |
| A2 | Daily Digest | 8:00 AM daily | Notification summary + appends stats to `digest.jsonl` |
| A3 | AI Insights | On-demand (sidebar button) | Ollama LLM analysis: priorities, risks, suggested next actions |

## AI Insights (Ollama)

A3 uses [Ollama](https://ollama.com) — a local LLM runner. No API key, no account.

```bash
# Install Ollama (macOS)
brew install ollama

# Start it
ollama serve

# Pull the default model (one-time, ~2GB)
ollama pull llama3.2
```

Once running, click **AI Insights** in the sidebar. Results appear in a panel inside the app. If Ollama is not running, the button shows a helpful error with install instructions.

## Magic Attribute

Add `Deadline: YYYY-MM-DD` as a custom attribute on any card. The hourly scanner fires a macOS notification when the deadline is within 24 hours or overdue.

## Data

| What | Where |
|------|-------|
| SQLite database | `server/omniboard.db` |
| localStorage fallback | `omniboard-state` key (Zustand persist) |
| Daily digest log | `digest.jsonl` (gitignored) |

The app works offline — if the server is unreachable, it loads from localStorage cache automatically. The sidebar shows `Synced` (green) or `Offline (localStorage)` (amber).
