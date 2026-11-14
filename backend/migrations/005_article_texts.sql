-- 005: per-language article text with its own provenance.
--
-- constitution_articles has columns for exactly two languages (text_en/text_gu) and ONE
-- source/page slot per article, so a second language would overwrite the first one's page
-- reference, and there is nowhere to store a third language at all. This table holds one
-- record per (article, language): the text exactly as found in the source, where it came
-- from, how it was extracted, and two independent quality states.
--
--   content_status       what kind of text this is (never upgraded automatically)
--   verification_status  whether a human has checked it (ingestion never sets 'verified')
--
-- The legacy text_en/text_gu columns stay (search index and existing API read them); the
-- importer writes both places for en/gu. Owner-written explanations are NOT stored here.

CREATE TABLE article_texts (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id          INTEGER NOT NULL REFERENCES constitution_articles(id) ON DELETE CASCADE,
    language            TEXT    NOT NULL,
    title               TEXT,
    body                TEXT,
    part_title          TEXT,
    chapter_title       TEXT,
    source_id           INTEGER REFERENCES legal_sources(id) ON DELETE SET NULL,
    source_locator      TEXT,
    source_pages        TEXT,
    edition             TEXT,
    extraction_method   TEXT    NOT NULL DEFAULT 'text_layer'
                          CHECK (extraction_method IN ('text_layer','ocr','manual_entry','structured_import','machine_translation')),
    content_status      TEXT    NOT NULL
                          CHECK (content_status IN ('OFFICIAL_SOURCE','OCR_REVIEW_REQUIRED','MACHINE_TRANSLATED','HUMAN_REVIEWED','VERIFIED')),
    verification_status TEXT    NOT NULL DEFAULT 'requires_human_verification'
                          CHECK (verification_status IN ('verified','requires_human_verification','unverified','outdated')),
    content_sha256      TEXT,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE (article_id, language)
);

CREATE INDEX idx_article_texts_language ON article_texts(language, content_status);
CREATE INDEX idx_article_texts_article  ON article_texts(article_id);
