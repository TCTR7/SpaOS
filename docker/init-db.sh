#!/bin/sh
# Tạo role ứng dụng KHÔNG phải superuser/owner để RLS có hiệu lực.
# Migration chạy bằng POSTGRES_USER (owner), app runtime chạy bằng APP_DB_USER.
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE ROLE ${APP_DB_USER} LOGIN PASSWORD '${APP_DB_PASSWORD}' NOSUPERUSER NOBYPASSRLS;
    GRANT CONNECT ON DATABASE ${POSTGRES_DB} TO ${APP_DB_USER};
    GRANT USAGE ON SCHEMA public TO ${APP_DB_USER};
    ALTER DEFAULT PRIVILEGES IN SCHEMA public
        GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO ${APP_DB_USER};
EOSQL
