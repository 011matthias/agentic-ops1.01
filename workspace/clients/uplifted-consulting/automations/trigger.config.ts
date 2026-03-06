import { defineConfig } from "@trigger.dev/sdk";
import { pythonExtension } from "@trigger.dev/python/extension";

export default defineConfig({
  project: "uplifted_consulting",
  runtime: "node",
  logLevel: "log",
  maxDuration: 300,
  build: {
    extensions: [
      pythonExtension({
        requirementsFile: "./requirements.txt",
      }),
    ],
  },
  dirs: ["src/trigger"],
});
