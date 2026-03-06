import { task } from "@trigger.dev/sdk/v3";
import { python } from "@trigger.dev/python";

/**
 * A1: Positive Reply Notifier
 *
 * Receives Smartlead EMAIL_REPLY webhook data, classifies the reply
 * using AI (OpenRouter), and sends a Slack notification if positive.
 *
 * Spec: specs/automations/a1-positive-reply-notifier.md
 */
export const positiveReplyNotifier = task({
  id: "a1-positive-reply-notifier",
  retry: {
    maxAttempts: 3,
  },
  run: async (payload: Record<string, unknown>) => {
    const result = await python.runScript(
      "./python/automations/positive_reply_notifier.py",
      [JSON.stringify(payload)]
    );
    return JSON.parse(result.stdout);
  },
});
