-- Reversal of 005. Per-language texts stored only in article_texts (languages other than
-- en/gu, and all per-language provenance) are lost; take a backup first.
DROP INDEX IF EXISTS idx_article_texts_article;
DROP INDEX IF EXISTS idx_article_texts_language;
DROP TABLE IF EXISTS article_texts;
