# Local LAN Docker Deployment Design

## Objective

Deploy Bovista on one Windows computer with Docker while making the web application available to phones and computers on the same trusted local network. The deployment must run the React frontend, FastAPI backend, PostgreSQL/PostGIS, Redis, migrations, and the durable outbox worker without Render or another cloud platform.

## Architecture

The deployment uses one root-level Docker Compose project with five long-running services and one migration job:

- `frontend` builds the Vite application and serves its static assets with Nginx.
- Nginx is the only LAN-facing application service and binds host port `8080` on all interfaces.
- Requests under `/api/` are reverse-proxied from Nginx to `api:10000`; all other requests use SPA fallback routing.
- `api` runs FastAPI only on the private Compose network.
- `worker` consumes the durable outbox using the restricted worker database role.
- `database` runs PostgreSQL 16 with PostGIS and persists data in a named volume.
- `redis` stores OTP and rate-limit state and persists data in a named volume.
- `migrate` runs Alembic and provisions the restricted runtime and worker database roles before the API and worker start.

Users access the application at `http://<host-lan-ip>:8080`. The browser and API therefore share one origin, avoiding per-device API URLs and CORS exceptions.

## Configuration and Secrets

An ignored local deployment environment file contains generated development secrets. The repository contains only a documented example file. Database passwords, JWT signing material, HMAC keys, refresh-token pepper, and the MFA encryption key must never be committed.

The local deployment runs with `ENVIRONMENT=development`. Farmer OTP delivery uses an explicit local-only adapter that writes the destination number and OTP code to API logs. The adapter must refuse to start when local OTP logging is enabled outside development mode. Operators retrieve codes with the documented Compose log command.

The frontend uses relative `/api/v1` requests. PostgreSQL and Redis expose no host ports. FastAPI is reachable only through Nginx. Only TCP port `8080` needs a Windows firewall rule for the private LAN profile.

## Startup and Failure Handling

Compose starts PostgreSQL and Redis first and waits for their health checks. The migration job then upgrades the schema and provisions restricted database roles. API and worker startup depend on successful migration completion. Nginx starts after the API is healthy.

Missing or invalid secrets, migration errors, database-role provisioning failures, or unhealthy dependencies must stop dependent services instead of producing a partially working deployment. Nginx returns an unavailable response while the API is unhealthy. Application and OTP diagnostics remain available through container logs.

PostgreSQL and Redis named volumes survive ordinary container recreation. Destructive volume removal is excluded from normal stop instructions. Backup documentation uses `pg_dump` before upgrades or host migration.

## Verification

Release verification consists of:

1. Validate the Compose model and environment interpolation.
2. Build frontend and backend container images.
3. Start the complete stack with the worker enabled by default.
4. Confirm the migration job exits successfully.
5. Confirm database, Redis, API, frontend, and worker containers are healthy or running as appropriate.
6. Request `/health` through `http://127.0.0.1:8080` and through the host LAN address.
7. Load the frontend through the same LAN address and confirm API requests use `/api/v1` on that origin.
8. Request a farmer OTP and confirm that the development code appears in API logs without exposing unrelated secrets.
9. Confirm the worker starts with the restricted worker database role.

## Operator Documentation

The backend README will document prerequisites, environment creation, secret generation, startup, health verification, LAN address discovery, private-network firewall configuration, OTP log viewing, routine logs, shutdown, restart, and PostgreSQL backup. It will clearly distinguish a local development deployment from an internet-facing production deployment.

## Out of Scope

- Public internet exposure, TLS termination, DNS, and router port forwarding.
- A production SMS provider.
- Multi-host orchestration or Kubernetes.
- Automatic off-machine backups.
- Changes to application workflows unrelated to local deployment.
