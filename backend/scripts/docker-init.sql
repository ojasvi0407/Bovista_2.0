CREATE EXTENSION IF NOT EXISTS postgis;
CREATE ROLE pashumitra_migrator LOGIN NOSUPERUSER NOBYPASSRLS CREATEDB CREATEROLE PASSWORD 'local-development-migrator-password-0001';
CREATE ROLE pashumitra_runtime LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE PASSWORD 'local-development-runtime-password-00001';
CREATE ROLE pashumitra_worker LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE PASSWORD 'local-development-worker-password-000001';
ALTER DATABASE pashumitra OWNER TO pashumitra_migrator;
GRANT ALL ON SCHEMA public TO pashumitra_migrator;
CREATE DATABASE pashumitra_test OWNER pashumitra_migrator;
\connect pashumitra_test
CREATE EXTENSION IF NOT EXISTS postgis;
GRANT ALL ON SCHEMA public TO pashumitra_migrator;
