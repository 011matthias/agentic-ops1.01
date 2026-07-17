CREATE TABLE IF NOT EXISTS "doc_comments" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
  "doc_host" text NOT NULL DEFAULT 'warme-wimmer',
  "page_slug" text NOT NULL,
  "parent_id" uuid,
  "author_id" text,
  "author_email" text NOT NULL,
  "author_name" text,
  "body_md" text NOT NULL,
  "deleted" boolean NOT NULL DEFAULT false,
  "edited_at" timestamp,
  "created_at" timestamp NOT NULL DEFAULT now()
);

DO $$ BEGIN
  ALTER TABLE "doc_comments" ADD CONSTRAINT "doc_comments_author_id_user_id_fk"
    FOREIGN KEY ("author_id") REFERENCES "user"("id") ON DELETE SET NULL;
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

CREATE INDEX IF NOT EXISTS "doc_comments_host_page_idx"
  ON "doc_comments" ("doc_host", "page_slug", "created_at");
CREATE INDEX IF NOT EXISTS "doc_comments_parent_idx"
  ON "doc_comments" ("parent_id");
