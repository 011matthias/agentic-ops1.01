export interface ModuleConfig {
  name: string;
  description: string;
  orchestrator: "trigger-dev" | "n8n" | "make" | "script";
  webhookPath: string;
  enabled: boolean;
}

export interface ModuleWebhookPayload {
  module: string;
  timestamp: string;
  data: Record<string, unknown>;
}
