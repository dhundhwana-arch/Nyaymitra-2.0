DROP INDEX IF EXISTS idx_import_changes_run;
DROP TABLE IF EXISTS import_changes;
-- Reversal of 006: drops the derived copies only; article_texts.body (the original) is untouched.
ALTER TABLE article_texts DROP COLUMN normalization_json;
ALTER TABLE article_texts DROP COLUMN body_normalized;
