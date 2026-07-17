CREATE TABLE IF NOT EXISTS "triage_feedback" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
  "log_row_id" text,
  "task_id" integer,
  "verdict" text NOT NULL,
  "soll_person" text,
  "author_name" text,
  "message" text,
  "created_at" timestamp NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS "triage_feedback_log_row_idx"
  ON "triage_feedback" ("log_row_id");
CREATE INDEX IF NOT EXISTS "triage_feedback_created_idx"
  ON "triage_feedback" ("created_at");
