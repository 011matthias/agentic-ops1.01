"""
A3: AI Task Insights
On-demand webhook — reads board state, sends to OpenRouter GPT-4o-mini,
returns structured insights (priorities, blockers, or next actions).
"""

import json
import sys
import logging
from typing import Any

import httpx

from .base import BaseAutomation
from ..config import get_settings
from ..clients.openrouter import OpenRouterClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a productivity assistant analyzing a Kanban board.
Return ONLY valid JSON matching this schema exactly:
{
  "insights": ["string", ...],
  "suggested_next": ["task title", ...],
  "risk_flags": ["string", ...],
  "summary": "one-sentence board health summary"
}
- insights: 3-5 bullet points about the board state
- suggested_next: top 3 task titles to work on now
- risk_flags: tasks at risk (overdue, blocked, missing deadlines)
- summary: one sentence
Return nothing else — just valid JSON."""

FOCUS_PROMPTS = {
    "priorities":    "Analyze task urgency and importance. Rank priorities. Highlight overdue items.",
    "blockers":      "Identify tasks that appear blocked or are blocking other tasks. Look for dependencies.",
    "next-actions":  "Suggest the top 3 concrete next actions to move the most impactful tasks forward.",
}


class AIInsights(BaseAutomation):
    automation_id = "a3-ai-insights"

    def initialize(self) -> None:
        self.settings = get_settings()
        if not self.settings.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY is required for AI insights")
        self.api_url = self.settings.omniboard_api_url
        self.openrouter = OpenRouterClient(api_key=self.settings.openrouter_api_key)
        self._payload: dict = getattr(self, "_input_payload", {})
        self.project_id = self._payload.get("projectId")
        self.focus = self._payload.get("focus", "priorities")

    def fetch_data(self) -> dict:
        resp = httpx.get(f"{self.api_url}/board-state", timeout=10)
        resp.raise_for_status()
        state = resp.json()

        if self.project_id:
            state["projects"] = [p for p in state["projects"] if p["id"] == self.project_id]
            state["cards"]    = [c for c in state["cards"] if c["projectId"] == self.project_id]

        return state

    def transform(self, data: dict) -> str:
        projects = {p["id"]: p["name"] for p in data["projects"]}
        cards    = data["cards"]
        stats    = data.get("stats", {})

        lines = []
        for proj in data["projects"]:
            proj_cards = [c for c in cards if c["projectId"] == proj["id"]]
            col_counts = {}
            for c in proj_cards:
                col_counts[c["columnId"]] = col_counts.get(c["columnId"], 0) + 1
            lines.append(
                f"Project: {proj['name']} "
                f"({col_counts.get('backlog',0)} backlog, {col_counts.get('todo',0)} todo, "
                f"{col_counts.get('in-progress',0)} in-progress, {col_counts.get('completed',0)} completed)"
            )
            for c in sorted(proj_cards, key=lambda x: x["position"]):
                attrs_str = ", ".join(f"{a['key']}: {a['value']}" for a in c.get("attributes", []))
                tags_str  = ", ".join(t["name"] for t in c.get("tags", []))
                meta = []
                if attrs_str: meta.append(attrs_str)
                if tags_str:  meta.append(f"tags: {tags_str}")
                meta_str = f" [{', '.join(meta)}]" if meta else ""
                lines.append(f"  [{c['columnId']}] {c['title']}{meta_str}")

        overdue = stats.get("overdue", [])
        if overdue:
            lines.append(f"\nOVERDUE ({len(overdue)}):")
            for c in overdue:
                lines.append(f"  {c['title']} ({projects.get(c['projectId'], '?')})")

        return "\n".join(lines)

    def execute(self, board_summary: str) -> dict:
        focus_instruction = FOCUS_PROMPTS.get(self.focus, FOCUS_PROMPTS["priorities"])
        user_message = f"{focus_instruction}\n\nBoard state:\n{board_summary}"

        if not board_summary.strip():
            return {
                "insights":      ["No tasks found on this board."],
                "suggested_next": [],
                "risk_flags":    [],
                "summary":       "The board is empty.",
            }

        response = self.openrouter.chat(
            model=self.settings.openrouter_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_message},
            ],
            max_tokens=500,
        )
        # OpenRouterClient returns a ChatCompletionResponse Pydantic model
        text = (response.choices[0].message.content or "").strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON block if model added surrounding text
            import re
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                return json.loads(match.group())
            logger.error(f"Could not parse AI response: {text[:200]}")
            return {
                "insights":      ["AI response could not be parsed."],
                "suggested_next": [],
                "risk_flags":    [],
                "summary":       "AI analysis failed. Check logs.",
            }

    def finalize(self, result: dict) -> None:
        logger.info(f"AI insights complete: {result.get('summary', '')}")


if __name__ == "__main__":
    automation = AIInsights()
    automation._input_payload = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
    result = automation.run(trigger="trigger-dev")
    print(json.dumps(result))
