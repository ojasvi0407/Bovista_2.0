CREATE EXTENSION IF NOT EXISTS postgis;
CREATE ROLE bovista_migrator LOGIN NOSUPERUSER NOBYPASSRLS CREATEDB CREATEROLE PASSWORD 'local-development-migrator-password-0001';
CREATE ROLE bovista_runtime LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE PASSWORD 'local-development-runtime-password-00001';
CREATE ROLE bovista_worker LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE PASSWORD 'local-development-worker-password-000001';
ALTER DATABASE bovista OWNER TO bovista_migrator;
GRANT ALL ON SCHEMA public TO bovista_migrator;
CREATE DATABASE bovista_test OWNER bovista_migrator;
\connect bovista_test
CREATE EXTENSION IF NOT EXISTS postgis;
GRANT ALL ON SCHEMA public TO bovista_migrator;
