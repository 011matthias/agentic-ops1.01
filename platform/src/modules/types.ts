export interface ModuleConfig {
  name: string;
  description: string;
  orchestrator: "trigger-dev" | "n8n" | "make" | "script";
  webhookPath: string;
  projectSlug: string;
  enabled: boolean;
}

export interface ModuleWebhookPayload {
  module: string;
  timestamp: string;
  status: "success" | "error" | "partial";
  itemCount?: number;
  durationMs?: number;
  data?: Record<string, unknown>;
}
