"""
A2: Daily Digest
8am daily — summarizes yesterday's completions and today's workload,
fires a macOS notification, and appends a JSON line to digest.jsonl.
"""

import json
import os
import subprocess
import sys
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

from .base import BaseAutomation
from ..config import get_settings

logger = logging.getLogger(__name__)

DIGEST_FILE = Path(__file__).parent / "digest.jsonl"


class DailyDigest(BaseAutomation):
    automation_id = "a2-daily-digest"

    def initialize(self) -> None:
        self.settings = get_settings()
        self.api_url = self.settings.omniboard_api_url
        self.now = datetime.now(timezone.utc)
        self.yesterday_start = (self.now - timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        self.yesterday_end = self.yesterday_start + timedelta(days=1)

    def fetch_data(self) -> dict:
        resp = httpx.get(f"{self.api_url}/board-state", timeout=10)
        resp.raise_for_status()
        return resp.json()

    def transform(self, data: dict) -> dict:
        cards = data.get("cards", [])

        completed_yesterday = []
        for card in cards:
            if card.get("columnId") != "completed":
                continue
            try:
                updated = datetime.fromisoformat(card["updatedAt"])
                if updated.tzinfo is None:
                    updated = updated.replace(tzinfo=timezone.utc)
                if self.yesterday_start <= updated < self.yesterday_end:
                    completed_yesterday.append(card)
            except (ValueError, KeyError):
                pass

        in_progress = [c for c in cards if c.get("columnId") == "in-progress"]
        todo        = [c for c in cards if c.get("columnId") == "todo"]
        backlog     = [c for c in cards if c.get("columnId") == "backlog"]
        overdue     = data.get("stats", {}).get("overdue", [])

        return {
            "completed_yesterday": len(completed_yesterday),
            "in_progress":         len(in_progress),
            "todo":                len(todo),
            "backlog":             len(backlog),
            "overdue":             len(overdue),
            "date":                self.now.strftime("%Y-%m-%d"),
        }

    def execute(self, data: dict) -> dict:
        message = (
            f"Yesterday: {data['completed_yesterday']} completed. "
            f"Today: {data['in_progress']} in progress, {data['todo']} todo"
            + (f", {data['overdue']} overdue" if data["overdue"] else "")
            + "."
        )

        try:
            subprocess.run(
                ["osascript", "-e", f'display notification "{message}" with title "OmniBoard — Good morning!"'],
                check=True,
                capture_output=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.info(f"[NOTIFY] OmniBoard — Good morning! {message}")

        # Append to digest log
        entry = {**data, "ts": self.now.isoformat()}
        with open(DIGEST_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")

        logger.info(f"Daily digest logged: {message}")
        return {**data, "message": message}

    def finalize(self, result: dict) -> None:
        logger.info(f"Daily digest complete for {result['date']}")


if __name__ == "__main__":
    payload = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
    digest = DailyDigest()
    result = digest.run(trigger="trigger-dev")
    print(json.dumps(result))
