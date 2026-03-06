import { task } from "@trigger.dev/sdk/v3";
import { python } from "@trigger.dev/python";
import { z } from "zod";

const PayloadSchema = z.object({
  projectId: z.string().optional(),
  focus: z.enum(["priorities", "blockers", "next-actions"]).default("priorities"),
});

export const aiInsights = task({
  id: "omni.ai.insights",
  retry: { maxAttempts: 1 }, // AI calls: don't retry aggressively
  run: async (payload: z.infer<typeof PayloadSchema>) => {
    const validated = PayloadSchema.parse(payload);
    const result = await python.runScript(
      "./python/automations/ai_insights.py",
      [JSON.stringify(validated)],
    );
    return JSON.parse(result.stdout);
  },
});
