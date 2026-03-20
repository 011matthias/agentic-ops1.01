CREATE TABLE IF NOT EXISTS "client_resources" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
  "client_id" text NOT NULL,
  "project_id" uuid,
  "title" text NOT NULL,
  "description" text,
  "type" text NOT NULL,
  "url" text NOT NULL,
  "category" text NOT NULL,
  "sort_order" integer DEFAULT 0 NOT NULL,
  "published" boolean DEFAULT false NOT NULL,
  "created_at" timestamp DEFAULT now() NOT NULL,
  "updated_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
DO $$ BEGIN
 ALTER TABLE "client_resources" ADD CONSTRAINT "client_resources_client_id_client_id_fk"
   FOREIGN KEY ("client_id") REFERENCES "public"."client"("id") ON DELETE cascade ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;
--> statement-breakpoint
DO $$ BEGIN
 ALTER TABLE "client_resources" ADD CONSTRAINT "client_resources_project_id_projects_id_fk"
   FOREIGN KEY ("project_id") REFERENCES "public"."projects"("id") ON DELETE set null ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;
