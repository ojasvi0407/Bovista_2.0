# Bovista backend foundation

This directory contains the government-operated livestock-health backend foundation for
farmers, veterinarians, para-veterinarians, laboratory staff, district officers, and
administrators. Its implemented scope is database, API, security, and explainable
triage/risk architecture.

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
The five-minute MFA challenge is persisted and single-use. Call `/api/v1/auth/refresh`
once per refresh token; reuse is treated as credential theft.

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

Tests use a real `bovista_test` PostgreSQL/PostGIS database configured through
`BOVISTA_TEST_DATABASE_URL`. The test runner refuses any database whose name does not end
in `_test` because fixtures rebuild the schema.

```powershell
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\black.exe --check .
.\.venv\Scripts\python.exe -m scripts.verify_db_invariants
```

Livestock records, rule-versioned decisions, outbreak transitions, and HMAC-chained audit
events are retention-oriented and have no ordinary hard-delete API. Backups, key rotation,
incident response, SMS gateway integration, and government deployment controls remain
operational responsibilities.

## Docker and Render

Build and run the production image locally:

```powershell
docker build -t bovista-api .
docker run --rm -p 10000:10000 --env-file .env -e ENVIRONMENT=production bovista-api
```

For a local PostGIS/Redis/API stack, copy `.env.example` to `.env`, replace the local
secrets, then run `docker compose up --build`. Compose creates separate `bovista` and
`bovista_test` databases and persistent named volumes. Apply migrations with
`docker compose run --rm api alembic upgrade head` before first use.

The image runs as a non-root user, listens on Render's `PORT`, and includes a `/health`
readiness check that verifies PostgreSQL connectivity. Do not pass secrets as Docker build
arguments.

The repository-root `render.yaml` defines the Docker web service, managed PostgreSQL,
health check, generated signing secrets, and `alembic upgrade head` as the pre-deploy
command. Set `CORS_ORIGINS` to a JSON list of exact frontend origins, set `REDIS_URL` to
a private Render Key Value connection URL, and provide a valid Fernet key for
`MFA_ENCRYPTION_KEY`. Also configure the two OTP delivery variables described above.
Enable PostGIS on the Render database; the initial migration also requests the extension.
Render pre-deploy commands require an eligible paid service plan.

For a manual Render service, use `backend` as the Docker context, `backend/Dockerfile` as
the Dockerfile, `/health` as the health-check path, and `alembic upgrade head` as the
pre-deploy command. The service must use a database role with `NOBYPASSRLS`.
