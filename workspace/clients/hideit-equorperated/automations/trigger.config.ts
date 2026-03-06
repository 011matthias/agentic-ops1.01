import { defineConfig } from "@trigger.dev/sdk";
import { pythonExtension } from "@trigger.dev/python/extension";

export default defineConfig({
  project: "hideit_equorperated", // Set TRIGGER_PROJECT_REF in .env if different
  runtime: "node",
  logLevel: "log",
  build: {
    extensions: [
      pythonExtension({
        requirementsFile: "./requirements.txt",
      }),
    ],
  },
  dirs: ["src/trigger"],
});
