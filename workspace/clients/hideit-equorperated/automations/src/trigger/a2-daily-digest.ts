import { schedules } from "@trigger.dev/sdk/v3";
import { python } from "@trigger.dev/python";

export const dailyDigest = schedules.task({
  id: "omni.digest.daily",
  cron: "0 8 * * *", // 8:00 AM daily
  retry: { maxAttempts: 2, minTimeoutInMs: 5000 },
  run: async () => {
    const result = await python.runScript(
      "./python/automations/daily_digest.py",
      [JSON.stringify({})],
    );
    return JSON.parse(result.stdout);
  },
});
