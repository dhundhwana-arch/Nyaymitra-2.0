-- 006: a separate, reversible "normalised" copy of OCR text.
--
-- article_texts.body is the text exactly as supplied (for OCR: the raw OCR output) and is
-- never rewritten by a clean-up step. When a clean-up is applied on request, its result
-- goes here together with the list of operations and counts, so the original can always be
-- compared and the step undone by setting these two columns back to NULL.
ALTER TABLE article_texts ADD COLUMN body_normalized TEXT;
ALTER TABLE article_texts ADD COLUMN normalization_json TEXT;

-- Journal of what each import run changed, so one run can be undone without restoring the
-- whole database (which would also discard complaints and uploads made since).
CREATE TABLE import_changes (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id            INTEGER NOT NULL REFERENCES ingest_runs(id) ON DELETE CASCADE,
    article_id        INTEGER NOT NULL,
    article_no        TEXT    NOT NULL,
    language          TEXT    NOT NULL,
    created_article   INTEGER NOT NULL DEFAULT 0,
    prev_article_json TEXT,              -- columns of constitution_articles before the run
    prev_text_json    TEXT,              -- article_texts row before the run (NULL = none)
    new_sha256        TEXT,              -- what the run wrote (to detect later edits)
    created_at        TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_import_changes_run ON import_changes(run_id);
