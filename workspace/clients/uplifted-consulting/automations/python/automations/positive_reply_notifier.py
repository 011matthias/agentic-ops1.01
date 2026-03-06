"""
Automation A1: Positive Reply Notifier

Spec: specs/automations/a1-positive-reply-notifier.md
Trigger: Webhook from Smartlead (EMAIL_REPLY) via Trigger.dev

Classifies incoming email replies using AI and sends
rich Slack notifications for positive responses.
"""

import json
import sys
import logging
from typing import Any

from .base import BaseAutomation
from ..clients.openrouter import OpenRouterClient, OpenRouterError
from ..clients.slack import SlackClient, SlackError
from ..config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# System prompt for AI classification
CLASSIFICATION_PROMPT = """You are an email reply classifier for sales outreach.

Analyze the email reply and determine if it's a POSITIVE response (interested in learning more,
wants to schedule a call, asks questions about the offering) or NOT POSITIVE (not interested,
out of office, unsubscribe request, negative response, spam, or irrelevant).

Respond with ONLY a JSON object in this exact format:
{
  "is_positive": true or false,
  "confidence": 0.0 to 1.0,
  "reasoning": "Brief explanation of classification"
}

Be strict - only mark as positive if there's clear interest or engagement.
Out of office replies are NOT positive.
Requests to unsubscribe are NOT positive.
Generic acknowledgments without interest are NOT positive."""


class PositiveReplyNotifierAutomation(BaseAutomation):
    """
    Automation that classifies email replies and notifies Slack for positive ones.

    This is a webhook-triggered automation that:
    1. Receives Smartlead EMAIL_REPLY webhook data
    2. Classifies the reply using OpenRouter AI
    3. Sends rich Slack notification if positive
    """

    automation_id = "positive_reply_notifier"

    def __init__(self, webhook_data: dict[str, Any] | None = None):
        self.webhook_data = webhook_data or {}
        self.openrouter: OpenRouterClient | None = None
        self.slack: SlackClient | None = None

    def initialize(self) -> None:
        """Initialize API clients."""
        if not settings.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY not configured")
        if not settings.slack_bot_token:
            raise ValueError("SLACK_BOT_TOKEN not configured")
        if not settings.slack_channel_id:
            raise ValueError("SLACK_CHANNEL_ID not configured")

        self.openrouter = OpenRouterClient(
            api_key=settings.openrouter_api_key,
            app_name="Uplifted Consulting Automations",
        )
        self.slack = SlackClient(token=settings.slack_bot_token)

    def fetch_data(self) -> dict[str, Any]:
        """Extract relevant data from webhook payload."""
        return {
            "reply_text": self.webhook_data.get("preview_text", ""),
            "from_email": self.webhook_data.get("from_email", ""),
            "to_email": self.webhook_data.get("to_email", ""),
            "to_name": self.webhook_data.get("to_name", "Unknown"),
            "subject": self.webhook_data.get("subject", ""),
            "campaign_name": self.webhook_data.get("campaign_name", "Unknown Campaign"),
            "campaign_id": self.webhook_data.get("campaign_id"),
            "inbox_link": self.webhook_data.get("ui_master_inbox_link", ""),
            "time_replied": self.webhook_data.get("time_replied", ""),
            "lead_correspondence": self.webhook_data.get("leadCorrespondence", {}),
        }

    def transform(self, data: dict[str, Any]) -> dict[str, Any]:
        """Classify the reply using AI."""
        if not self.openrouter:
            raise RuntimeError("OpenRouter client not initialized")

        reply_text = data.get("reply_text", "")
        if not reply_text.strip():
            return {
                **data,
                "classification": {
                    "is_positive": False,
                    "confidence": 1.0,
                    "reasoning": "Empty reply text",
                },
            }

        context = f"""
Campaign: {data.get('campaign_name')}
From: {data.get('from_email')}
To: {data.get('to_name')} ({data.get('to_email')})
Subject: {data.get('subject')}

Reply:
{reply_text}
"""

        try:
            response = self.openrouter.chat(
                model=settings.openrouter_model,
                messages=[
                    {"role": "system", "content": CLASSIFICATION_PROMPT},
                    {"role": "user", "content": context},
                ],
                temperature=0.1,
                max_tokens=200,
            )

            content = response.choices[0].message.content or "{}"
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            classification = json.loads(content.strip())

            if "is_positive" not in classification:
                classification["is_positive"] = False
            if "confidence" not in classification:
                classification["confidence"] = 0.5
            if "reasoning" not in classification:
                classification["reasoning"] = "No reasoning provided"

            logger.info(
                f"Classified reply from {data.get('from_email')}: "
                f"positive={classification['is_positive']}, "
                f"confidence={classification['confidence']}"
            )

        except (json.JSONDecodeError, OpenRouterError) as e:
            logger.error(f"Classification error: {e}")
            classification = {
                "is_positive": False,
                "confidence": 0.0,
                "reasoning": f"Classification failed: {e}",
            }

        return {
            **data,
            "classification": classification,
        }

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        """Send Slack notification if positive."""
        if not self.slack:
            raise RuntimeError("Slack client not initialized")

        classification = data.get("classification", {})
        is_positive = classification.get("is_positive", False)

        if not is_positive:
            logger.info(
                f"Reply from {data.get('from_email')} classified as not positive, skipping notification"
            )
            return {
                "action": "skipped",
                "reason": "not_positive",
                "classification": classification,
            }

        blocks = self._build_slack_blocks(data)

        try:
            response = self.slack.post_message(
                channel=settings.slack_channel_id,
                text=f"Positive reply from {data.get('to_name')} ({data.get('from_email')})",
                blocks=blocks,
            )
            logger.info(f"Sent Slack notification for positive reply from {data.get('from_email')}")

            return {
                "action": "notified",
                "channel": settings.slack_channel_id,
                "message_ts": response.ts,
                "classification": classification,
            }

        except SlackError as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return {
                "action": "failed",
                "error": str(e),
                "classification": classification,
            }

    def finalize(self, result: dict[str, Any]) -> None:
        """Cleanup and close clients."""
        if self.openrouter:
            self.openrouter.close()
        if self.slack:
            self.slack.close()

    def _build_slack_blocks(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Build rich Slack Block Kit message."""
        classification = data.get("classification", {})
        confidence = classification.get("confidence", 0)
        confidence_pct = f"{confidence:.0%}"

        reply_preview = data.get("reply_text", "")[:500]
        if len(data.get("reply_text", "")) > 500:
            reply_preview += "..."

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "Positive Reply Received",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Lead:*\n{data.get('to_name', 'Unknown')}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Email:*\n{data.get('from_email', 'Unknown')}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Campaign:*\n{data.get('campaign_name', 'Unknown')}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Confidence:*\n{confidence_pct}",
                    },
                ],
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Reply Preview:*\n>{reply_preview}",
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"*AI Reasoning:* {classification.get('reasoning', 'N/A')}",
                    },
                ],
            },
        ]

        inbox_link = data.get("inbox_link")
        if inbox_link:
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Open in Smartlead",
                            "emoji": True,
                        },
                        "url": inbox_link,
                        "action_id": "open_smartlead",
                    },
                ],
            })

        return blocks


if __name__ == "__main__":
    payload = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}

    # Extract webhook_data from payload (Trigger.dev passes it as the task payload)
    automation = PositiveReplyNotifierAutomation(webhook_data=payload)
    result = automation.run(
        dry_run=payload.get("dry_run", False),
    )
    print(json.dumps(result))
