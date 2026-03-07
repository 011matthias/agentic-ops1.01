import type { ModuleConfig } from "./types";

const modules: ModuleConfig[] = [
  // Phase 2: Register automation modules here
  // Example:
  // {
  //   name: "upwork-scraper",
  //   description: "Scrapes Upwork for relevant leads",
  //   orchestrator: "trigger-dev",
  //   webhookPath: "/api/modules/upwork-scraper",
  //   enabled: false,
  // },
];

export function getModule(name: string): ModuleConfig | undefined {
  return modules.find((m) => m.name === name);
}

export function getEnabledModules(): ModuleConfig[] {
  return modules.filter((m) => m.enabled);
}
