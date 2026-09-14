# PashuMitra backend foundation

This directory contains the government-operated livestock-health backend foundation for
farmers, veterinarians, para-veterinarians, laboratory staff, district officers, and
administrators. It implements database, API, security, explainable triage/risk, clinical
operations, laboratory workflow, surveillance, and durable event-delivery architecture.

## Runtime

- Python 3.12 or newer
- PostgreSQL 16 with PostGIS 3
- Redis 6 or newer for production OTP storage and rate limits

Create a virtual environment, install `requirements-dev.txt` for local development (the
production container installs only `requirements.txt`), copy `.env.example` to `.env`, and
replace every secret. Generate `MFA_ENCRYPTION_KEY` with
`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
The PostgreSQL application role must be `NOSUPERUSER NOBYPASSRLS`; forced row-level
security is ineffective for superusers.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\uvicorn.exe app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`; interactive OpenAPI documentation is
at `/docs`. The container entrypoint reads `PORT` and defaults to `10000`.

Production must set `ENVIRONMENT=production`, an explicit CORS allowlist, unique random
values for the JWT signing key, refresh pepper, OTP HMAC key, audit HMAC key, and MFA
encryption key, plus managed PostgreSQL and Redis URLs. `OTP_DELIVERY_URL` must be the
government SMS gateway's HTTPS webhook and `OTP_DELIVERY_TOKEN` its bearer credential;
the gateway receives `mobile_number` and `code` as JSON. Never reuse one secret for two
purposes. Access tokens default to ten minutes; refresh tokens are opaque, stored only as
peppered hashes, rotated per use, and revoked as a family when replay is detected.

## Authentication examples

Request and verify a farmer's single-use five-minute OTP:

```http
POST /api/v1/auth/otp/request
Content-Type: application/json

{"mobile_number":"+919999999999","device_id":"phone-1"}
```

```http
POST /api/v1/auth/otp/verify
Content-Type: application/json

{"mobile_number":"+919999999999","device_id":"phone-1","code":"123456"}
```

Staff first call `/api/v1/auth/staff/login` with their government identifier and password,
then submit the returned challenge and current TOTP to `/api/v1/auth/staff/mfa/verify`.
The five-minute MFA challenge is persisted, single-use, and locked after five failed
attempts. Call `/api/v1/auth/refresh`
once per refresh token; reuse is treated as credential theft.

Create the first staff administrator from a trusted shell. The command prompts securely
for the password, TOTP seed, and current TOTP rather than exposing credentials in process
arguments:

```powershell
.\.venv\Scripts\python.exe -m scripts.provision_staff
```

## Operational APIs

Farm and herd resources support scoped create, list, detail, versioned update, and
retention-safe archive operations at `/api/v1/farms` and `/api/v1/herds`. Animals use the
same scoped CRUD pattern at `/api/v1/animals`; list endpoints use cursor pagination.
Archiving a parent with active children is rejected.

Authorized veterinary staff record immutable vaccinations and treatments at
`/api/v1/vaccinations` and `/api/v1/treatments`. Corrections use explicit `/reverse`
commands with a reason, preserving the original clinical record. The vaccination due
endpoint excludes future, reversed, and superseded doses.

Laboratory samples follow the enforced sequence REFERRED, COLLECTED, RECEIVED, PROCESSING,
RESULTED, REVIEWED under `/api/v1/lab`. Each state change has its own role-authorized
command, an immutable transition record, audit evidence, and transactional recipient
alerts. Veterinary cases expose list/detail/history plus review, refer, resume, and close
commands; cases with unresolved laboratory work cannot close.

Administrators manage location, disease, and symptom reference data through
`/api/v1/locations`, `/api/v1/diseases`, and `/api/v1/symptoms`. Versioned triage and risk
rule packs are published through `/api/v1/rule-packs`; published contents are protected
from mutation by database triggers.

## Reports and decisions

Every mutation requires `Idempotency-Key`. Report submission also requires an `If-Match`
header containing the current quoted version. Farmers can read only their records. Vets
and para-vets can read identifiable reports only under their one assigned hierarchy path.
District officers use aggregate data unless an active, expiring case-review grant exists.
PostgreSQL forced RLS backs up the service policy.

```http
POST /api/v1/disease-reports
Authorization: Bearer ACCESS_TOKEN
Idempotency-Key: phone-1:report-7
Content-Type: application/json

{"client_generated_id":"018f0000-0000-7000-8000-000000000001","farm_id":"018f0000-0000-7000-8000-000000000002","species":"CATTLE","symptoms":[{"code":"FEVER"}],"affected_count":3,"mortality_count":1,"onset_date":"2026-09-10","latitude":"28.6139","longitude":"77.2090"}
```

After submission, call `POST /api/v1/disease-reports/{id}/triage` and
`POST /api/v1/disease-reports/{id}/risk-score`. Triage is advisory only and never a
diagnosis. Both engines persist snapshot hash, rule/config version, evidence,
contributions, missing inputs, and confidence. HIGH or CRITICAL risk atomically opens a
veterinary case, creates an alert, and requests outbreak analysis.

Analysis may create only a `POTENTIAL` outbreak. Only an in-jurisdiction district officer
may call `/api/v1/outbreaks/{id}/declare` or `/dismiss`, and a written reason is mandatory.
Weather can strengthen an existing spatial/temporal cluster but cannot create one alone.

## Alerts and surveillance dashboard

Authenticated users can list their visible alerts with cursor pagination at
`GET /api/v1/alerts` and acknowledge one with
`POST /api/v1/alerts/{alert_id}/acknowledge`. Acknowledgement requires an
`Idempotency-Key`, is replay-safe, and writes audit and outbox records atomically.

District officers and administrators can call `GET /api/v1/dashboard/summary`. The
dashboard returns aggregates only—never farmer identity, mobile number, animal tag, or
point coordinates—and supports `date_from`, `date_to`, `species`, `disease_code`, and
`location_id` filters. `group_by` accepts `location`, `species`, `disease`, or `date`;
location grouping also accepts `location_level`. District officers cannot request a
location outside their active geographic assignment. Counts cover animals, active cases,
reports, mortality, current vaccination coverage, active outbreaks, high-risk locations,
and pending laboratory samples.

## Verification

Tests use a real `pashumitra_test` PostgreSQL/PostGIS database configured through
`PASHUMITRA_TEST_DATABASE_URL`. The test runner refuses any database whose name does not end
in `_test` because fixtures rebuild the schema.

```powershell
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\black.exe --check .
.\.venv\Scripts\python.exe -m scripts.verify_db_invariants
.\.venv\Scripts\python.exe -m scripts.verify_history
```

Livestock records, rule-versioned decisions, outbreak transitions, and HMAC-chained audit
events are retention-oriented and have no ordinary hard-delete API. Backups, key rotation,
incident response, SMS gateway integration, and government deployment controls remain
operational responsibilities.

## Local Docker deployment on Windows and a trusted LAN

This deployment is for development on a trusted private network. It does not configure
TLS or safely expose PashuMitra to the public internet. Install Docker Desktop with the WSL 2
backend, start Docker Desktop, and run the following commands from the repository root.

Generate the ignored local environment file. The command refuses to replace an existing
file; use `-Force` only when you intentionally want to rotate all local secrets.

```powershell
.\scripts\initialize-local-docker.ps1
docker compose --env-file .env.local-docker config --quiet
docker compose --env-file .env.local-docker up --build -d
docker compose --env-file .env.local-docker ps -a
```

The `migrate` job must show exit code `0`. The database, Redis, API, and frontend should
be healthy, and the worker should remain running. The only host port is TCP 8080 on the
frontend; PostgreSQL, Redis, and FastAPI remain on the private Compose network.

Check the API through the same Nginx endpoint used by browsers, then load the frontend:

```powershell
Invoke-RestMethod http://127.0.0.1:8080/health
Invoke-WebRequest http://127.0.0.1:8080/
```

Find the host's active LAN address and repeat the health check from the host or another
device on the same network. Open `http://<LAN-IP>:8080` on phones and computers.

```powershell
$lanIp = Get-NetIPConfiguration |
  Where-Object { $_.NetAdapter.Status -eq "Up" -and $_.IPv4DefaultGateway } |
  Select-Object -ExpandProperty IPv4Address |
  Select-Object -First 1 -ExpandProperty IPAddress
Invoke-RestMethod "http://${lanIp}:8080/health"
```

If another device cannot connect, run this once in an elevated PowerShell window to allow
only private-profile inbound TCP traffic on port 8080:

```powershell
New-NetFirewallRule -DisplayName "PashuMitra LAN HTTP" -Direction Inbound `
  -Action Allow -Protocol TCP -LocalPort 8080 -Profile Private
```

Farmer OTP delivery is deliberately logged only in this development deployment. Request
an OTP in the application or through `/api/v1/auth/otp/request`, then view the code without
printing the environment file:

```powershell
docker compose --env-file .env.local-docker logs api |
  Select-String "local_development_otp"
```

Routine operations preserve the named PostgreSQL and Redis volumes:

```powershell
docker compose --env-file .env.local-docker logs --tail 100 api worker
docker compose --env-file .env.local-docker restart
docker compose --env-file .env.local-docker down
```

Do not add `--volumes` to the normal shutdown command. Before an upgrade or host move,
create a PostgreSQL custom-format backup from inside the private database container:

```powershell
New-Item -ItemType Directory -Force .\backups | Out-Null
docker compose --env-file .env.local-docker exec -T database `
  pg_dump -U pashumitra_migrator -d pashumitra --format=custom --file=/tmp/pashumitra.dump
docker compose --env-file .env.local-docker cp `
  database:/tmp/pashumitra.dump .\backups\pashumitra.dump
```

## Docker and Render

Build and run the production image locally:

```powershell
docker build -t pashumitra-api .
docker run --rm -p 10000:10000 --env-file .env -e ENVIRONMENT=production pashumitra-api
```

For a local PostGIS/Redis/API stack, copy `.env.example` to `.env`, replace the local
secrets, then run `docker compose up --build`. Compose creates separate `pashumitra` and
`pashumitra_test` databases and persistent named volumes. Apply migrations with
`docker compose run --rm api alembic upgrade head` before first use.

The image runs as a non-root user, listens on Render's `PORT`, and includes a `/health`
readiness check that verifies PostgreSQL connectivity. Do not pass secrets as Docker build
arguments.

The repository-root `render.yaml` defines the Docker web service, durable background
worker, managed PostgreSQL, health check, generated signing secrets, and
`alembic upgrade head` as the pre-deploy command. Set `CORS_ORIGINS` to a JSON list of
exact frontend origins, set `REDIS_URL` to
a private Render Key Value connection URL, and provide a valid Fernet key for
`MFA_ENCRYPTION_KEY`. Also configure the two OTP delivery variables described above.
Enable PostGIS on the Render database; the initial migration also requests the extension.
Render pre-deploy commands require an eligible paid service plan.

The worker runs `python -m scripts.worker`. Set `WORKER_USER_ID` to an active provisioned
administrator service account. Set `EVENT_DELIVERY_URL` to the government's HTTPS event
gateway and `EVENT_DELIVERY_TOKEN` to a distinct secret of at least 32 characters. The
worker processes outbreak-analysis requests internally and forwards all other outbox
events with an idempotency key, bounded retries, and exponential backoff. Render copies
the API's security configuration into the worker so audit signatures remain consistent.

For a manual Render service, use `backend` as the Docker context, `backend/Dockerfile` as
the Dockerfile, `/health` as the health-check path, and `alembic upgrade head` as the
pre-deploy command. The service must use a database role with `NOBYPASSRLS`.
Run the worker as a separate always-on background service using the same image, database,
and security configuration.
