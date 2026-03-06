import { task } from "@trigger.dev/sdk/v3";
import { python } from "@trigger.dev/python";

/**
 * Example automation task.
 *
 * This is a thin TypeScript wrapper that calls a Python automation script.
 * The actual business logic lives in python/automations/example.py.
 *
 * Copy this file as a starting point for new automations.
 */
export const exampleAutomation = task({
  id: "example",
  retry: {
    maxAttempts: 3,
  },
  run: async (payload: Record<string, unknown>) => {
    const result = await python.runScript(
      "./python/automations/example.py",
      [JSON.stringify(payload)]
    );
    return JSON.parse(result.stdout);
  },
});
