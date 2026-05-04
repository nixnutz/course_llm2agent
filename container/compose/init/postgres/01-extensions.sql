-- Runs once on first cluster init via the official postgres
-- /docker-entrypoint-initdb.d/ hook. Re-runs only after the data
-- volume is wiped (e.g. `make state-prune`).
--
-- Idempotent role/grant setup lives in init/postgres/role-bootstrap.sh
-- so it can re-apply on every `compose up`.

CREATE EXTENSION IF NOT EXISTS vector;
-- Optional, often useful for RAG fuzzy match; uncomment if needed:
-- CREATE EXTENSION IF NOT EXISTS pg_trgm;
