# Clinical Operations Extension Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the existing FastAPI foundation with scoped animal/farm CRUD, vaccinations, treatments, lab workflow, alerts, dashboard APIs, Docker deployment, and integration tests.

**Architecture:** The existing SQLAlchemy model/service/router pattern remains the boundary. New clinical records attach to the existing `Animal`, `VeterinaryCase`, and `DiseaseReport` aggregates; services authorize by `CurrentPrincipal`, write audit/outbox events atomically, and use explicit workflow commands instead of open status edits. Dashboard endpoints query de-identified aggregates only.

**Tech Stack:** Python 3.14 runtime (compatible with project minimum 3.12), FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic, PostgreSQL/PostGIS, pytest, Docker.

**Spec:** `docs/superpowers/specs/2026-09-10-livestock-backend-core-architecture-design.md`

## Global Constraints

- Preserve UUIDv7, UTC, version, audit, outbox, idempotency, RLS, and safe error conventions already implemented.
- Farmers access only owned data; staff must be in their assigned jurisdiction; district officers receive aggregate-only dashboard data.
- Vaccinations and treatments are immutable clinical records; corrections use explicit amendment/reversal history.
- Laboratory lifecycle is `REFERRED → COLLECTED → RECEIVED → PROCESSING → RESULTED → REVIEWED` and every transition is role-authorized.
- All write endpoints require `Idempotency-Key` and return existing response envelopes.
- Write and observe each test failing before production implementation.

---

### Task 1: Scoped farm, herd, and animal CRUD

**Files:**
- Create: `backend/app/schemas/animals.py`, `backend/app/repositories/animals.py`, `backend/app/services/animals.py`, `backend/app/api/v1/animals.py`
- Modify: `backend/app/api/v1/router.py`, `backend/alembic/versions/0005_clinical_operations.py`
- Test: `backend/tests/api/test_animals.py`

**Interfaces:** Produces `AnimalService.create/list/get/update/delete(principal, ...)` and `/api/v1/farms`, `/herds`, `/animals` routes.

- [x] Write a failing test proving a farmer can create/list an own-farm animal and cannot read another farmer’s animal.
- [x] Run `backend/.venv/Scripts/python.exe -m pytest tests/api/test_animals.py -v` and observe route-not-found behavior.
- [x] Implement Pydantic schemas, repository queries scoped by ownership/location, versioned updates, soft deletion, idempotency, and atomic audit/outbox writes.
- [x] Re-run the test and confirm both allowed and denied behavior.

### Task 2: Vaccination and treatment records

**Files:**
- Create: `backend/app/models/clinical.py`, `backend/app/schemas/clinical.py`, `backend/app/repositories/clinical.py`, `backend/app/services/clinical.py`, `backend/app/api/v1/clinical.py`
- Modify: `backend/app/models/__init__.py`, `backend/app/api/v1/router.py`, `backend/alembic/versions/0005_clinical_operations.py`
- Test: `backend/tests/api/test_vaccinations.py`, `backend/tests/api/test_treatments.py`

**Interfaces:** Produces `VaccinationService.record/list_due()` and `TreatmentService.record/list()`.

- [x] Write failing tests proving an authorized veterinarian records a vaccination with batch and next due date; due endpoint excludes future doses; farmer cannot create treatment; unauthorized staff cannot read a treatment.
- [x] Run the two test modules and observe missing route/model failures.
- [x] Implement `vaccinations` and `treatments` tables, non-empty vaccine/medicine validation, positive dosage/duration checks, animal/case ownership checks, immutable write behavior, due-date index, and route/service policy enforcement.
- [x] Re-run tests and confirm CRUD, due filtering, validation, and scope behavior.

### Task 3: Laboratory referral and result lifecycle

**Files:**
- Create: `backend/app/models/laboratory.py`, `backend/app/schemas/laboratory.py`, `backend/app/repositories/laboratory.py`, `backend/app/services/laboratory.py`, `backend/app/api/v1/laboratory.py`
- Modify: `backend/app/models/__init__.py`, `backend/app/api/v1/router.py`, `backend/alembic/versions/0005_clinical_operations.py`
- Test: `backend/tests/api/test_laboratory.py`

**Interfaces:** Produces `LaboratoryService.refer/collect/receive/start_processing/publish_result/review()` and `/api/v1/lab/samples`, `/api/v1/lab/results`.

- [x] Write failing tests that reject a lab result before receipt, reject a farmer publishing results, and create a recipient-scoped lab-result alert after valid publication.
- [x] Run the laboratory test module and observe missing lifecycle services/routes.
- [x] Implement sample/result/transition tables, the fixed state machine, specimen metadata, chain-of-custody fields, result validation, role checks, and transactional case/alert/audit/outbox updates.
- [x] Re-run tests and confirm valid sequence succeeds and invalid transitions return `409`.

### Task 4: Alert read/acknowledge API and surveillance dashboard

**Files:**
- Create: `backend/app/schemas/dashboard.py`, `backend/app/repositories/dashboard.py`, `backend/app/services/{alerts,dashboard}.py`, `backend/app/api/v1/{alerts,dashboard}.py`
- Modify: `backend/app/api/v1/router.py`
- Test: `backend/tests/api/test_alerts.py`, `backend/tests/api/test_dashboard.py`

**Interfaces:** Produces `/api/v1/alerts`, `/api/v1/alerts/{id}/acknowledge`, and `/api/v1/dashboard/summary`.

- [x] Write failing tests proving users see only recipient/owned alerts and district-dashboard output contains counts by allowed dimensions but no farmer name, mobile number, animal tag, or exact point coordinate.
- [x] Run dashboard/alert tests and observe unavailable endpoints.
- [x] Implement cursor-paginated alert reads, recipient authorization, acknowledgement audit records, and aggregate queries for animals, active cases, reports, mortality, vaccination coverage, outbreaks, high-risk locations, and pending samples filtered by jurisdiction/date/species/disease.
- [x] Re-run tests and confirm de-identification, aggregation, filters, and alert access.

### Task 5: Docker, operational documentation, and full verification

**Files:**
- Create: `backend/Dockerfile`, `backend/docker-compose.yml`, `backend/.dockerignore`
- Modify: `backend/.env.example`, `backend/README.md`, `backend/requirements.txt`
- Test: `backend/tests/test_deployment_contract.py`

**Interfaces:** Produces a Render-compatible container that binds `$PORT`, executes migrations as an explicit release command, and reports `/health`.

- [x] Write failing deployment-contract tests checking documented `PORT`, required environment variables, `.dockerignore` exclusion of `.env`/`.venv`, and health endpoint.
- [x] Run the deployment test and observe missing Docker artifacts.
- [x] Implement a non-root Python 3.12 slim Docker image, production Uvicorn startup, Compose PostgreSQL/PostGIS and Redis services, Render configuration instructions, and complete setup/test/migration/security documentation.
- [x] Run `pytest -q`, `ruff check .`, `black --check .`, and `alembic upgrade head`; GitHub CI performs the Docker build and health smoke because Docker is unavailable on this workstation.

### Task 6: CRUD corrections, contract cleanup, and documentation maintenance

**Files:**
- Modify: `backend/app/api/v1/animals.py`, `backend/app/services/animals.py`, `backend/app/schemas/animals.py`, and affected route/model modules
- Modify: `backend/README.md`, `backend/.env.example`, `backend/requirements.txt`
- Test: `backend/tests/api/test_crud_corrections.py`, `backend/tests/test_documentation_contract.py`

**Interfaces:** Preserves stable `/api/v1` names, adds missing CRUD actions, and keeps response envelopes and error codes backwards-compatible.

- [x] Write focused tests for delete/soft-delete semantics, stale-version conflicts, canonical route names, and required environment-variable documentation.
- [x] Run those tests and observe each missing correction fail before implementation.
- [x] Implement only the required CRUD/API corrections, update renamed symbols and imports consistently, and keep UI-facing payload fields stable; this workspace has no frontend, so no unrelated UI code is introduced.
- [x] Update README examples and `.env.example` without real secrets, run Ruff/Black, and execute the focused plus full test suite.

## Plan self-review

- Coverage: Tasks 1–4 fulfill the previously deferred CRUD, vaccination, treatment, lab, alerts, and dashboard scope; Task 5 covers Docker and deployment documentation.
- Boundaries: Existing core authentication/RBAC/report/risk/outbreak behavior remains unmodified except for router/model registration and required clinical relations.
- TDD: each task begins with a concrete observable behavior before implementation.
- Maintenance coverage: Task 6 covers CRUD corrections, README, `.env.example`, small API/UI-facing contract changes, renaming, simple tests, formatting, and documentation.
