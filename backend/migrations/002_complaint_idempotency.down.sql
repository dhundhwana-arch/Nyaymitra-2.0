-- Down migration for 002_complaint_idempotency.sql
DROP INDEX IF EXISTS idx_complaints_fingerprint;
DROP INDEX IF EXISTS uq_complaints_client_request;
ALTER TABLE complaints DROP COLUMN fingerprint;
ALTER TABLE complaints DROP COLUMN client_request_id;
