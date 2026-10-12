-- Read-only role for the application (the app only ever runs SELECTs).
-- Run once as an admin, passing the password via a psql variable so it never
-- lands in git or shell history files:
--   psql "$ADMIN_DATABASE_URL" -v app_password="'<strong-password>'" -f sql/readonly_role.sql
-- Then point DATABASE_URL at app_readonly (on Supabase use the pooler host,
-- user "app_readonly.<project-ref>").

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_readonly') THEN
        CREATE ROLE app_readonly LOGIN;
    END IF;
END $$;

ALTER ROLE app_readonly WITH PASSWORD :app_password
    NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT CONNECTION LIMIT 10;
ALTER ROLE app_readonly SET default_transaction_read_only = on;
ALTER ROLE app_readonly SET statement_timeout = '10s';

REVOKE ALL ON SCHEMA public FROM app_readonly;
GRANT USAGE ON SCHEMA public TO app_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO app_readonly;
