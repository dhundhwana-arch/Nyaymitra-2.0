-- NYAYMITRA 2.0 — initial schema (migration 001)
-- Conventions:
--   * every legal/knowledge row carries provenance + verification status
--   * no PII is stored without an access token (hash only)
--   * legacy junk data lives only in legacy_import_chunks (admin-only)

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------- provenance
CREATE TABLE legal_sources (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_key      TEXT    NOT NULL UNIQUE,
    title           TEXT    NOT NULL,
    publisher       TEXT    NOT NULL,
    -- official         : published by the Government / court / statutory body itself
    -- official_mirror  : official content hosted on a government sub-portal
    -- third_party      : reputable non-official mirror (must be flagged to users)
    -- owner_authored   : authored by the project owner (paraphrase, not law text)
    source_type     TEXT    NOT NULL CHECK (source_type IN
                        ('official','official_mirror','third_party','owner_authored')),
    url             TEXT,
    document_ref    TEXT,
    published_on    TEXT,          -- ISO date when the source itself was published
    retrieved_on    TEXT,          -- ISO date when we obtained a copy
    licence_note    TEXT,
    notes           TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- --------------------------------------------------------------- constitution
CREATE TABLE constitution_articles (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    article_key             TEXT    NOT NULL UNIQUE,     -- e.g. 'article-14'
    article_no              TEXT    NOT NULL,            -- e.g. '14' or 'Preamble'
    article_label           TEXT    NOT NULL,            -- e.g. 'Article 14'
    part_no                 TEXT,
    part_title              TEXT,
    chapter_title           TEXT,
    title_en                TEXT,
    title_gu                TEXT,
    text_en                 TEXT,
    text_gu                 TEXT,
    citizen_explanation_en  TEXT,
    citizen_explanation_gu  TEXT,
    -- verified_source_text : the text above is the published text of the article
    -- owner_authored_summary: a human-written summary/paraphrase, not the statute
    -- not_available        : we knowingly do not have the text (never guess)
    text_status             TEXT    NOT NULL DEFAULT 'not_available'
                              CHECK (text_status IN
                                ('verified_source_text','owner_authored_summary','not_available')),
    verification_status     TEXT    NOT NULL DEFAULT 'requires_human_verification'
                              CHECK (verification_status IN
                                ('verified','requires_human_verification','unverified','outdated')),
    source_id               INTEGER REFERENCES legal_sources(id) ON DELETE SET NULL,
    source_locator          TEXT,             -- page / section / anchor inside the source
    source_url              TEXT,
    last_checked_at         TEXT,             -- NULL = never checked by a human
    checked_by              TEXT,
    notes                   TEXT,
    sort_order              INTEGER NOT NULL DEFAULT 0,
    created_at              TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at              TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_articles_no            ON constitution_articles(article_no);
CREATE INDEX idx_articles_part          ON constitution_articles(part_no);
CREATE INDEX idx_articles_verification  ON constitution_articles(verification_status);
CREATE UNIQUE INDEX uq_articles_no_part ON constitution_articles(article_no, IFNULL(part_no, ''));

CREATE TABLE article_sources (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id  INTEGER NOT NULL REFERENCES constitution_articles(id) ON DELETE CASCADE,
    source_id   INTEGER NOT NULL REFERENCES legal_sources(id) ON DELETE CASCADE,
    locator     TEXT,
    note        TEXT,
    UNIQUE (article_id, source_id)
);

-- Full-text search (external content table, kept in sync by triggers)
CREATE VIRTUAL TABLE constitution_fts USING fts5(
    article_label,
    title_en, title_gu,
    text_en, text_gu,
    citizen_explanation_en, citizen_explanation_gu,
    content='constitution_articles',
    content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
);

CREATE TRIGGER constitution_ftsi AFTER INSERT ON constitution_articles BEGIN
    INSERT INTO constitution_fts(rowid, article_label, title_en, title_gu, text_en, text_gu,
                                 citizen_explanation_en, citizen_explanation_gu)
    VALUES (new.id, new.article_label, new.title_en, new.title_gu, new.text_en, new.text_gu,
            new.citizen_explanation_en, new.citizen_explanation_gu);
END;

CREATE TRIGGER constitution_ftsd AFTER DELETE ON constitution_articles BEGIN
    INSERT INTO constitution_fts(constitution_fts, rowid, article_label, title_en, title_gu,
                                 text_en, text_gu, citizen_explanation_en, citizen_explanation_gu)
    VALUES ('delete', old.id, old.article_label, old.title_en, old.title_gu, old.text_en,
            old.text_gu, old.citizen_explanation_en, old.citizen_explanation_gu);
END;

CREATE TRIGGER constitution_ftsu AFTER UPDATE ON constitution_articles BEGIN
    INSERT INTO constitution_fts(constitution_fts, rowid, article_label, title_en, title_gu,
                                 text_en, text_gu, citizen_explanation_en, citizen_explanation_gu)
    VALUES ('delete', old.id, old.article_label, old.title_en, old.title_gu, old.text_en,
            old.text_gu, old.citizen_explanation_en, old.citizen_explanation_gu);
    INSERT INTO constitution_fts(rowid, article_label, title_en, title_gu, text_en, text_gu,
                                 citizen_explanation_en, citizen_explanation_gu)
    VALUES (new.id, new.article_label, new.title_en, new.title_gu, new.text_en, new.text_gu,
            new.citizen_explanation_en, new.citizen_explanation_gu);
END;

-- ------------------------------------------------- triage guides (navigation)
CREATE TABLE triage_guides (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    guide_key           TEXT    NOT NULL UNIQUE,
    category_en         TEXT    NOT NULL,
    category_gu         TEXT    NOT NULL,
    summary_en          TEXT,
    summary_gu          TEXT,
    steps_en            TEXT    NOT NULL DEFAULT '[]',    -- JSON array
    steps_gu            TEXT    NOT NULL DEFAULT '[]',
    documents_en        TEXT    NOT NULL DEFAULT '[]',
    documents_gu        TEXT    NOT NULL DEFAULT '[]',
    keywords            TEXT    NOT NULL DEFAULT '[]',    -- JSON array, gu/en/hi
    department_key      TEXT,
    source_id           INTEGER REFERENCES legal_sources(id) ON DELETE SET NULL,
    verification_status TEXT    NOT NULL DEFAULT 'requires_human_verification'
                            CHECK (verification_status IN ('verified','requires_human_verification','unverified','outdated')),
    last_checked_at     TEXT,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ------------------------------------------- departments & official channels
CREATE TABLE departments (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    department_key      TEXT    NOT NULL UNIQUE,
    name_en             TEXT    NOT NULL,
    name_gu             TEXT    NOT NULL,
    jurisdiction        TEXT,             -- central | state:gujarat | district | taluka
    purpose_en          TEXT,
    purpose_gu          TEXT,
    portal_url          TEXT,
    portal_label        TEXT,
    helpline            TEXT,
    email               TEXT,
    address             TEXT,
    source_id           INTEGER REFERENCES legal_sources(id) ON DELETE SET NULL,
    -- verified             : a human checked the channel against the official source
    -- requires_human_verification / unverified / outdated
    verification_status TEXT    NOT NULL DEFAULT 'requires_human_verification'
                            CHECK (verification_status IN ('verified','requires_human_verification','unverified','outdated')),
    verified_on         TEXT,
    verified_by         TEXT,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ---------------------------------------------------------------- complaints
CREATE TABLE complaints (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    reference           TEXT    NOT NULL UNIQUE,           -- NYM-XXXXXXXX
    access_token_hash   TEXT    NOT NULL,                  -- sha256 of the user's token
    language            TEXT    NOT NULL DEFAULT 'gu' CHECK (language IN ('gu','en')),
    category            TEXT    NOT NULL,
    title               TEXT    NOT NULL,
    description         TEXT    NOT NULL,
    summary             TEXT    NOT NULL,
    incident_date       TEXT,
    location            TEXT,
    district            TEXT,
    state               TEXT,
    respondent          TEXT,
    contact_phone       TEXT,
    contact_email       TEXT,
    consent_given       INTEGER NOT NULL DEFAULT 0 CHECK (consent_given IN (0,1)),
    status              TEXT    NOT NULL DEFAULT 'draft'
                            CHECK (status IN ('draft','submitted','in_review','closed')),
    submitted_at        TEXT,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_complaints_status  ON complaints(status);
CREATE INDEX idx_complaints_created ON complaints(created_at);

-- ----------------------------------------------------------------- documents
CREATE TABLE documents (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    stored_name         TEXT    NOT NULL UNIQUE,      -- random, no user-controlled path
    original_name       TEXT    NOT NULL,
    mime_type           TEXT    NOT NULL,
    size_bytes          INTEGER NOT NULL,
    sha256              TEXT    NOT NULL,
    document_kind       TEXT    NOT NULL DEFAULT 'other'
                            CHECK (document_kind IN ('evidence','identity','legal_notice','other')),
    owner_token_hash    TEXT    NOT NULL,
    complaint_id        INTEGER REFERENCES complaints(id) ON DELETE SET NULL,
    extracted_text      TEXT,
    extraction_status   TEXT    NOT NULL DEFAULT 'not_processed'
                            CHECK (extraction_status IN
                                ('not_processed','extracted','ocr_unavailable','extraction_failed','too_large')),
    ocr_confidence      REAL,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_documents_complaint ON documents(complaint_id);

-- ---------------------------------------------------- logging / monitoring
CREATE TABLE query_logs (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id          TEXT,
    language            TEXT    NOT NULL DEFAULT 'gu',
    query_text          TEXT,                        -- redacted copy (see logging.redact)
    query_hash          TEXT,
    category            TEXT,
    provider            TEXT,
    latency_ms          INTEGER,
    status              TEXT    NOT NULL DEFAULT 'ok',
    error_code          TEXT,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_query_logs_created ON query_logs(created_at);

CREATE TABLE ai_answers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    query_log_id    INTEGER REFERENCES query_logs(id) ON DELETE CASCADE,
    provider        TEXT,
    model           TEXT,
    grounded        INTEGER NOT NULL DEFAULT 0,
    degraded        INTEGER NOT NULL DEFAULT 0,
    citations_json  TEXT    NOT NULL DEFAULT '[]',
    answer_text     TEXT,
    warnings_json   TEXT    NOT NULL DEFAULT '[]',
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE feedback (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    target_type     TEXT    NOT NULL CHECK (target_type IN ('ai_answer','article','department')),
    target_ref      TEXT    NOT NULL,
    reason          TEXT    NOT NULL CHECK (reason IN
                        ('incorrect_law','outdated','unsafe_advice','wrong_department','other')),
    message         TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    at          TEXT    NOT NULL DEFAULT (datetime('now')),
    actor       TEXT    NOT NULL,              -- 'admin' | 'monitor' | 'system' | 'public'
    action      TEXT    NOT NULL,
    target      TEXT,
    detail      TEXT,                          -- JSON, already redacted
    ip_hash     TEXT
);

CREATE INDEX idx_audit_at ON audit_log(at);

CREATE TABLE error_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    at              TEXT    NOT NULL DEFAULT (datetime('now')),
    request_id      TEXT,
    method          TEXT,
    path            TEXT,
    status_code     INTEGER,
    error_type      TEXT,
    message         TEXT,          -- redacted
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_error_at ON error_log(at);

-- ------------------------------------------------- legacy quarantine (admin)
CREATE TABLE legacy_import_chunks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    legacy_id       INTEGER,
    article_no      TEXT,
    part            TEXT,
    title           TEXT,
    text            TEXT,
    remedy_text     TEXT,           -- generated by the old importer: NEVER shown as law
    script          TEXT,
    archive_ref     TEXT,
    imported_at     TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_legacy_no ON legacy_import_chunks(article_no);

CREATE TABLE ingest_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_key      TEXT,
    source_file     TEXT,
    started_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    finished_at     TEXT,
    articles_found  INTEGER NOT NULL DEFAULT 0,
    articles_written INTEGER NOT NULL DEFAULT 0,
    duplicates      INTEGER NOT NULL DEFAULT 0,
    missing_numbers TEXT    NOT NULL DEFAULT '[]',
    report_json     TEXT    NOT NULL DEFAULT '{}',
    status          TEXT    NOT NULL DEFAULT 'running'
);
