-- 002_complaint_idempotency.sql
-- Duplicate-submission protection for the complaint wizard.
--
-- * client_request_id is generated once per wizard session by the browser, so a
--   double-click, a retry after a timeout or a back-button resubmit returns the
--   SAME complaint instead of creating a second one.
-- * fingerprint lets the server refuse an identical submission inside a short
--   window even when the client sends no idempotency key (older clients, curl).
ALTER TABLE complaints ADD COLUMN client_request_id TEXT;
ALTER TABLE complaints ADD COLUMN fingerprint TEXT;

CREATE UNIQUE INDEX uq_complaints_client_request
    ON complaints(client_request_id)
    WHERE client_request_id IS NOT NULL;

CREATE INDEX idx_complaints_fingerprint ON complaints(fingerprint, created_at);
