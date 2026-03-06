import { schedules } from "@trigger.dev/sdk/v3";
import { python } from "@trigger.dev/python";

export const deadlineScanner = schedules.task({
  id: "omni.scan.deadlines",
  cron: "0 * * * *", // Every hour
  retry: { maxAttempts: 2, minTimeoutInMs: 5000 },
  run: async () => {
    const result = await python.runScript(
      "./python/automations/deadline_scanner.py",
      [JSON.stringify({})],
    );
    return JSON.parse(result.stdout);
  },
});
