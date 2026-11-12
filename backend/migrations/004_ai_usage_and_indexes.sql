-- 004: token accounting for AI answers, plus indexes for the admin queries.
--
-- ai_answers recorded what was said, to whom and whether it was grounded, but not how
-- much it cost. Without token counts an operator cannot see which provider/model is
-- expensive or behaving differently, and cannot answer "what did the free tier use today?".
--
-- The indexes below back the admin console and the usage report: recent answers by date,
-- answers joined to their query log, feedback by date, and the review queue filters by
-- verification status.

ALTER TABLE ai_answers ADD COLUMN prompt_tokens     INTEGER;
ALTER TABLE ai_answers ADD COLUMN completion_tokens INTEGER;

CREATE INDEX idx_ai_answers_created   ON ai_answers(created_at);
CREATE INDEX idx_ai_answers_query_log ON ai_answers(query_log_id);
CREATE INDEX idx_feedback_created     ON feedback(created_at);
CREATE INDEX idx_triage_verification  ON triage_guides(verification_status);
CREATE INDEX idx_departments_verification ON departments(verification_status);
