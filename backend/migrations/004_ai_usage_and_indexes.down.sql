-- Reversal of 004. The token columns are dropped (their data cannot be reconstructed);
-- the indexes are dropped first because SQLite cannot drop a column an index references.
DROP INDEX IF EXISTS idx_departments_verification;
DROP INDEX IF EXISTS idx_triage_verification;
DROP INDEX IF EXISTS idx_feedback_created;
DROP INDEX IF EXISTS idx_ai_answers_query_log;
DROP INDEX IF EXISTS idx_ai_answers_created;

ALTER TABLE ai_answers DROP COLUMN completion_tokens;
ALTER TABLE ai_answers DROP COLUMN prompt_tokens;
