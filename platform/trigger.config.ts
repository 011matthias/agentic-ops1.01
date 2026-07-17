import { defineConfig } from "@trigger.dev/sdk"

export default defineConfig({
  project: "proj_apgqpncwvgscghguviup",
  dirs: ["./src/trigger"],
  runtime: "node",
  maxDuration: 3600,
  retries: {
    enabledInDev: false,
    default: {
      maxAttempts: 1,
      minTimeoutInMs: 1000,
      maxTimeoutInMs: 30000,
      factor: 2,
    },
  },
  build: {
    // Agent SDK spawns cli.js as a subprocess — must not be tree-shaken
    external: ["@anthropic-ai/claude-agent-sdk"],
  },
})
