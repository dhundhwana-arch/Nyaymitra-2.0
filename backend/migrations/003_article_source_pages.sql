-- 003_article_source_pages.sql
-- Provenance: which pages of the supplied document an article's text came from.
-- For a text file the value is "1"; for a PDF it is "12" or "12-14".
ALTER TABLE constitution_articles ADD COLUMN source_pages TEXT;
