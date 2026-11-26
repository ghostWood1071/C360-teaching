#!/bin/sh
set -eu

create_role_and_database() {
  role_name=$1
  role_password=$2
  database_name=$3

  psql --set=ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres \
    --set=role_name="$role_name" --set=role_password="$role_password" --set=database_name="$database_name" <<'SQL'
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'role_name', :'role_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'role_name') \gexec
SELECT format('ALTER ROLE %I WITH LOGIN PASSWORD %L', :'role_name', :'role_password') \gexec
SELECT format('CREATE DATABASE %I OWNER %I', :'database_name', :'role_name')
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'database_name') \gexec
SELECT format('ALTER DATABASE %I OWNER TO %I', :'database_name', :'role_name') \gexec
SELECT format('GRANT CONNECT, TEMPORARY ON DATABASE %I TO %I', :'database_name', :'role_name') \gexec
SQL
}

create_role_and_database "$AIRFLOW_DB_USER" "$AIRFLOW_DB_PASSWORD" "$AIRFLOW_DB_NAME"
create_role_and_database "$METASTORE_DB_USER" "$METASTORE_DB_PASSWORD" "$METASTORE_DB_NAME"
create_role_and_database "$RANGER_DB_USER" "$RANGER_DB_PASSWORD" "$RANGER_DB_NAME"

if [ "${CREATE_SOURCE_DATABASES:-false}" = "true" ]; then
  create_role_and_database "$CORE_BANKING_DB_USER" "$CORE_BANKING_DB_PASSWORD" "$CORE_BANKING_DB_NAME"
  create_role_and_database "$CRM_DB_USER" "$CRM_DB_PASSWORD" "$CRM_DB_NAME"
fi
