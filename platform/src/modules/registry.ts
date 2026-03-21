import type { ModuleConfig } from "./types";

const modules: ModuleConfig[] = [
  {
    name: "meji-enquiry-followup",
    description: "Enquiry follow-up email sequence",
    orchestrator: "make",
    webhookPath: "/api/modules/meji-enquiry-followup",
    projectSlug: "meji-media",
    enabled: true,
  },
];

export function getModule(name: string): ModuleConfig | undefined {
  return modules.find((m) => m.name === name);
}

export function getEnabledModules(): ModuleConfig[] {
  return modules.filter((m) => m.enabled);
}
