-- 0007: add selection_anchor JSONB column to doc_comments.
--
-- Inline-highlight comments anchor on a W3C TextQuoteSelector triple
-- {exact, prefix, suffix} stored as JSONB. NULL means "page-level comment"
-- (the existing flat-thread mode), so old rows keep working unchanged.
--
-- GIN index supports future filter queries like "all comments anchored on
-- a specific phrase" if we ever need cross-page search. For the immediate
-- per-page fetch (GET /api/wimmer-comments?pageSlug=X), the existing
-- (doc_host, page_slug, created_at) index continues to do the work.

ALTER TABLE "doc_comments" ADD COLUMN IF NOT EXISTS "selection_anchor" jsonb;

CREATE INDEX IF NOT EXISTS "doc_comments_selection_idx"
  ON "doc_comments" USING gin ("selection_anchor");
