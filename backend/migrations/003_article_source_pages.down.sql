-- Down migration for 003_article_source_pages.sql
ALTER TABLE constitution_articles DROP COLUMN source_pages;
