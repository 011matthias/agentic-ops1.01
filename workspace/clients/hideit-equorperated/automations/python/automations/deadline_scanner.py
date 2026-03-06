"""
A1: Deadline Scanner
Hourly cron — scans all cards with a "Deadline" attribute and fires macOS
notifications for cards that are overdue or due within 24 hours.
"""

import json
import subprocess
import sys
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from .base import BaseAutomation
from ..config import get_settings

logger = logging.getLogger(__name__)


class DeadlineScanner(BaseAutomation):
    automation_id = "a1-deadline-scanner"

    def initialize(self) -> None:
        self.settings = get_settings()
        self.api_url = self.settings.omniboard_api_url
        self.now = datetime.now(timezone.utc)
        self.in_24h = self.now + timedelta(hours=24)

    def fetch_data(self) -> dict:
        resp = httpx.get(f"{self.api_url}/board-state", timeout=10)
        resp.raise_for_status()
        return resp.json()

    def transform(self, data: dict) -> list[dict]:
        cards = data.get("cards", [])
        projects = {p["id"]: p["name"] for p in data.get("projects", [])}
        flagged = []

        for card in cards:
            attrs = card.get("attributes", [])
            deadline_attr = next((a for a in attrs if a["key"] == "Deadline"), None)
            if not deadline_attr:
                continue
            try:
                deadline = datetime.fromisoformat(deadline_attr["value"])
                if deadline.tzinfo is None:
                    deadline = deadline.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                logger.warning(f"Skipping card {card['id']}: invalid Deadline value '{deadline_attr['value']}'")
                continue

            if deadline < self.now:
                flagged.append({
                    "card": card,
                    "project_name": projects.get(card["projectId"], "Unknown"),
                    "deadline": deadline,
                    "urgency": "overdue",
                })
            elif deadline < self.in_24h:
                hours_until = int((deadline - self.now).total_seconds() / 3600)
                flagged.append({
                    "card": card,
                    "project_name": projects.get(card["projectId"], "Unknown"),
                    "deadline": deadline,
                    "urgency": "due-soon",
                    "hours_until": hours_until,
                })

        return flagged

    def execute(self, data: list[dict]) -> dict:
        sent = 0
        for item in data:
            card = item["card"]
            project = item["project_name"]
            urgency = item["urgency"]

            if urgency == "overdue":
                message = f"[OVERDUE] {card['title']} ({project})"
            else:
                h = item.get("hours_until", 0)
                message = f"Due in {h}h: {card['title']} ({project})"

            try:
                subprocess.run(
                    ["osascript", "-e", f'display notification "{message}" with title "OmniBoard Deadline"'],
                    check=True,
                    capture_output=True,
                )
                sent += 1
                logger.info(f"Notification sent: {message}")
            except subprocess.CalledProcessError as e:
                logger.error(f"osascript failed for card {card['id']}: {e}")
            except FileNotFoundError:
                # Not on macOS — log only
                logger.info(f"[NOTIFY] {message}")
                sent += 1

        return {"notifications_sent": sent, "cards_scanned": len(data)}

    def finalize(self, result: dict) -> None:
        logger.info(
            f"Deadline scan complete: {result['notifications_sent']} notifications sent "
            f"for {result['cards_scanned']} flagged cards"
        )


if __name__ == "__main__":
    payload = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
    scanner = DeadlineScanner()
    result = scanner.run(trigger="trigger-dev")
    print(json.dumps(result))
