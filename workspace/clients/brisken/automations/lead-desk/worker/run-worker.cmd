@echo off
rem Lead Desk worker tick, invoked by the LeadDeskWorker scheduled task.
rem Runs from the PINNED worktree this file lives in (never the dev checkout)
rem and keeps state + secrets in the gitignored main-clone context dir.
set WORKER_HOME=C:\Users\neuma_p1qrsic\Repo\agentic-ops1\workspace\clients\brisken\context\lead-desk-worker
cd /d "%~dp0.."
uv run --extra web --extra worker lead-desk-worker tick --home "%WORKER_HOME%" >> "%WORKER_HOME%\task.log" 2>&1
