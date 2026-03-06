import { defineConfig } from "@trigger.dev/sdk";
import { pythonExtension } from "@trigger.dev/python/extension";

export default defineConfig({
  project: "<project-ref>", // Replace with your Trigger.dev project ref
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
