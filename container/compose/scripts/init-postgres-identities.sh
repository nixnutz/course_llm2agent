#!/bin/sh
set -eu
# Purpose: ensure Postgres roles/databases for LiteLLM and Phoenix exist.
# Called by: one-shot container service "postgres_init_identities".
# Notes: idempotent setup using admin credentials from environment.

: "${POSTGRES_HOST:?POSTGRES_HOST is required}"
: "${POSTGRES_PORT:?POSTGRES_PORT is required}"
: "${POSTGRES_ADMIN_DB:?POSTGRES_ADMIN_DB is required}"
: "${POSTGRES_ADMIN_USER:?POSTGRES_ADMIN_USER is required}"
: "${POSTGRES_ADMIN_PASSWORD:?POSTGRES_ADMIN_PASSWORD is required}"

: "${LITELLM_DB:?LITELLM_DB is required}"
: "${LITELLM_USER:?LITELLM_USER is required}"
: "${LITELLM_PASSWORD:?LITELLM_PASSWORD is required}"

: "${PHOENIX_DB:?PHOENIX_DB is required}"
: "${PHOENIX_USER:?PHOENIX_USER is required}"
: "${PHOENIX_PASSWORD:?PHOENIX_PASSWORD is required}"

export PGPASSWORD="${POSTGRES_ADMIN_PASSWORD}"

psql_base() {
  psql \
    -h "${POSTGRES_HOST}" \
    -p "${POSTGRES_PORT}" \
    -U "${POSTGRES_ADMIN_USER}" \
    -d "${POSTGRES_ADMIN_DB}" \
    -v ON_ERROR_STOP=1 "$@"
}

psql_db() {
  db_name="$1"
  shift
  psql \
    -h "${POSTGRES_HOST}" \
    -p "${POSTGRES_PORT}" \
    -U "${POSTGRES_ADMIN_USER}" \
    -d "${db_name}" \
    -v ON_ERROR_STOP=1 "$@"
}

ensure_role() {
  role_name="$1"
  role_password="$2"
  psql_base <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '${role_name}') THEN
    CREATE ROLE "${role_name}" LOGIN PASSWORD '${role_password}';
  ELSE
    ALTER ROLE "${role_name}" WITH LOGIN PASSWORD '${role_password}';
  END IF;
END
\$\$;
SQL
}

ensure_db() {
  db_name="$1"
  owner_name="$2"
  if ! psql_base -tAc "SELECT 1 FROM pg_database WHERE datname = '${db_name}'" | grep -q 1; then
    psql_base -c "CREATE DATABASE \"${db_name}\" OWNER \"${owner_name}\";"
  fi
}

grant_db_owner() {
  db_name="$1"
  owner_name="$2"
  psql_base <<SQL
ALTER DATABASE "${db_name}" OWNER TO "${owner_name}";
GRANT ALL PRIVILEGES ON DATABASE "${db_name}" TO "${owner_name}";
SQL
}

ensure_vector_extension() {
  db_name="$1"
  psql_db "${db_name}" -c "CREATE EXTENSION IF NOT EXISTS vector;"
}

echo "Ensuring dedicated Postgres roles/databases for LiteLLM and Phoenix..."

ensure_role "${LITELLM_USER}" "${LITELLM_PASSWORD}"
ensure_role "${PHOENIX_USER}" "${PHOENIX_PASSWORD}"

ensure_db "${LITELLM_DB}" "${LITELLM_USER}"
ensure_db "${PHOENIX_DB}" "${PHOENIX_USER}"

grant_db_owner "${LITELLM_DB}" "${LITELLM_USER}"
grant_db_owner "${PHOENIX_DB}" "${PHOENIX_USER}"

ensure_vector_extension "${LITELLM_DB}"
ensure_vector_extension "${PHOENIX_DB}"

echo "Postgres identities/databases are ready."
