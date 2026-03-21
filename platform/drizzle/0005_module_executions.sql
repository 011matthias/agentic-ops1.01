CREATE TABLE IF NOT EXISTS "module_executions" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
  "project_id" uuid NOT NULL REFERENCES "projects"("id") ON DELETE CASCADE,
  "module_name" text NOT NULL,
  "status" text NOT NULL,
  "item_count" integer DEFAULT 0 NOT NULL,
  "duration_ms" integer,
  "metadata" text,
  "executed_at" timestamp NOT NULL,
  "created_at" timestamp DEFAULT now() NOT NULL
);
