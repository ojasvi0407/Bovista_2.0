# Livestock Backend Core Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a runnable, tested backend vertical slice implementing the approved database, API, security, and explainable risk/triage architecture.

**Architecture:** A modular FastAPI monolith uses async SQLAlchemy repositories over PostgreSQL/PostGIS. Services enforce ownership and jurisdiction, persist audit/outbox records in the same transaction, and expose farmer OTP plus staff password/TOTP authentication. Disease reports feed versioned deterministic triage, risk scoring, veterinary escalation, and potential-outbreak analysis.

**Tech Stack:** Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic, PostgreSQL 16 with PostGIS 3, Redis, Argon2id, PyJWT, PyOTP, pytest, Ruff, Black.

**Spec:** `docs/superpowers/specs/2026-09-10-livestock-backend-core-architecture-design.md`

## Global Constraints

- Scope is limited to database architecture, API architecture, security architecture, and risk/triage architecture.
- Use UUIDv7-compatible identifiers and timezone-aware UTC timestamps.
- PostgreSQL/PostGIS is the production and integration-test database; do not substitute SQLite for persistence tests.
- Farmer authentication uses short-lived, single-use mobile OTPs. Staff authentication uses Argon2id passwords plus TOTP MFA.
- A staff account has exactly one active geographic assignment.
- Farmers see only owned data; vets and para-vets see identifiable records only inside their assigned jurisdiction; district officers receive aggregates unless a case-review grant exists.
- Access JWTs are short-lived. Opaque refresh tokens are hashed, rotated, and replay-detected.
- All state-changing endpoints require `Idempotency-Key`; mutations write audit and outbox records atomically.
- Triage is advisory and explainable. It never claims a definitive veterinary diagnosis.
- Risk is a versioned deterministic score from 0 to 100. HIGH/CRITICAL results create a veterinary case and alert.
- Automated analysis creates only a potential outbreak. Only a district officer may declare or dismiss it.
- Write each test first, run it to observe the expected failure, then add the minimum implementation.
- The workspace is not a Git repository, so do not run commit steps unless Git is initialized later.

---

## File map

```text
backend/
  app/
    main.py
    api/{dependencies,errors,responses}.py
    api/v1/{router,auth,disease_reports,decisions,outbreaks}.py
    core/{config,crypto,middleware}.py
    db/{base,session}.py
    models/{identity,geography,reports,decisions,surveillance,trust}.py
    repositories/{reports,surveillance}.py
    schemas/{auth,reports,decisions,outbreaks}.py
    services/{auth,authorization,reports,decisions,outbreaks,trust}.py
    risk/{contracts,triage,scoring,outbreaks}.py
  alembic/versions/0001_core_architecture.py
  tests/{api,integration,services}/
  alembic.ini pyproject.toml requirements.txt .env.example README.md
```

Routes own HTTP mapping only. Services own policies and transactions. Repositories own SQL. Risk modules are pure deterministic code and do not import FastAPI or SQLAlchemy.

---

### Task 1: Runnable API shell and safe response contract

**Files:**
- Create: `backend/pyproject.toml`, `backend/requirements.txt`, `backend/.env.example`
- Create: `backend/app/main.py`, `backend/app/core/config.py`, `backend/app/core/middleware.py`
- Create: `backend/app/api/responses.py`, `backend/app/api/errors.py`, `backend/app/api/v1/router.py`
- Test: `backend/tests/api/test_health.py`

**Interfaces:**
- Produces: `get_settings() -> Settings`
- Produces: `envelope(data: T, *, meta: dict[str, Any] | None = None) -> dict[str, Any]`
- Produces: `create_app() -> FastAPI` and `GET /health`

- [x] **Step 1: Write the failing health and security-header tests**

```python
from fastapi.testclient import TestClient
from app.main import create_app


def test_health_uses_stable_envelope() -> None:
    response = TestClient(create_app()).get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "data": {"status": "healthy"},
        "meta": {"request_id": response.headers["x-request-id"]},
        "error": None,
    }


def test_security_headers_are_present() -> None:
    response = TestClient(create_app()).get("/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
```

- [x] **Step 2: Run `cd backend; pytest tests/api/test_health.py -v`**

Expected: FAIL because `app.main` does not exist.

- [x] **Step 3: Implement the app factory and response envelope**

```python
# app/api/responses.py
from typing import Any, TypeVar

T = TypeVar("T")


def envelope(data: T, *, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"data": data, "meta": meta or {}, "error": None}
```

```python
# app/main.py
def create_app() -> FastAPI:
    app = FastAPI(title="Livestock Health API", version="1.0.0")

    @app.get("/health")
    async def health(request: Request) -> dict[str, object]:
        return envelope(
            {"status": "healthy"},
            meta={"request_id": request.state.request_id},
        )
    return app


app = create_app()
```

Add request-ID middleware, the tested headers, explicit CORS origins from `Settings`, and safe exception responses shaped as `{"data": null, "meta": {"request_id": ...}, "error": {"code": ..., "message": ...}}`. Configure Python 3.12, Ruff, Black, and pytest asyncio mode.

- [x] **Step 4: Run `cd backend; pytest tests/api/test_health.py -v; ruff check .; black --check .`**

Expected: all checks pass.

---

### Task 2: PostgreSQL/PostGIS schema and transactional trust primitives

**Files:**
- Create: `backend/app/db/base.py`, `backend/app/db/session.py`
- Create: `backend/app/models/{identity,geography,reports,decisions,surveillance,trust}.py`
- Create: `backend/app/services/trust.py`
- Create: `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/versions/0001_core_architecture.py`
- Test: `backend/tests/conftest.py`, `backend/tests/services/test_trust.py`

**Interfaces:**
- Produces: `Base`, `UUID7PrimaryKeyMixin`, `TimestampMixin`, `VersionMixin`
- Produces: `async_session_factory`, `set_rls_context()`, `record_audit()`, `enqueue_event()`, `claim_idempotency()`

- [x] **Step 1: Write failing audit/outbox/idempotency tests**

```python
@pytest.mark.asyncio
async def test_mutation_audit_and_outbox_commit_together(session, farmer, report_id):
    async with session.begin():
        claim = await claim_idempotency(session, farmer.id, "report-001", "sha256:req")
        await record_audit(session, farmer.id, "report.create", "report", report_id, True)
        await enqueue_event(session, "report.created", report_id, {"id": str(report_id)})
    assert claim.is_replay is False
    assert await session.scalar(audit_count_for(report_id)) == 1
    assert await session.scalar(outbox_count_for(report_id)) == 1


@pytest.mark.asyncio
async def test_idempotency_replay_returns_original_result(session, farmer):
    first = await claim_idempotency(session, farmer.id, "same-key", "sha256:req")
    await first.store_response(201, {"id": "server-id"})
    second = await claim_idempotency(session, farmer.id, "same-key", "sha256:req")
    assert second.is_replay is True
    assert second.response_body == {"id": "server-id"}
```

- [x] **Step 2: Run `cd backend; pytest tests/services/test_trust.py -v`**

Expected: FAIL on missing persistence modules.

- [x] **Step 3: Implement shared database primitives and the migration**

```python
class Base(DeclarativeBase):
    type_annotation_map = {dict[str, object]: JSONB}


class UUID7PrimaryKeyMixin:
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
```

Enable PostGIS and create the approved identity, geography, report, decision, surveillance, audit, idempotency, and outbox tables. Add checks for non-negative counts, location hierarchy levels, risk range 0–100, and outbreak states. Add unique indexes for `(reporter_id, client_generated_id)`, one active staff assignment, and `(actor_id, idempotency_key)`. Add GiST geometry indexes and B-tree indexes for hierarchy path, report date/status, rules, risks, and outbreaks. `record_audit` HMAC-chains canonical entries under a PostgreSQL advisory lock. Trust helpers flush but never commit independently.

- [x] **Step 4: Run `cd backend; alembic upgrade head; pytest tests/services/test_trust.py -v`**

Expected: migration and tests pass against PostgreSQL/PostGIS.

---

### Task 3: Farmer OTP and staff password/TOTP authentication

**Files:**
- Create: `backend/app/core/crypto.py`, `backend/app/schemas/auth.py`
- Create: `backend/app/services/auth.py`, `backend/app/api/dependencies.py`, `backend/app/api/v1/auth.py`
- Modify: `backend/app/api/v1/router.py`
- Test: `backend/tests/api/test_auth.py`

**Interfaces:**
- Produces: `CurrentPrincipal(user_id, roles, location_path)`
- Produces: farmer OTP request/verify, staff login/MFA verify, refresh, logout, and `/me`
- Produces: opaque hashed refresh-token rotation with family replay detection

- [x] **Step 1: Write failing single-use OTP and refresh replay tests**

```python
def test_farmer_otp_is_single_use(client, otp_sender):
    client.post("/api/v1/auth/otp/request", json={"mobile_number": "+919999999999"})
    code = otp_sender.last_code
    payload = {"mobile_number": "+919999999999", "code": code, "device_id": "phone-1"}
    assert client.post("/api/v1/auth/otp/verify", json=payload).status_code == 200
    assert client.post("/api/v1/auth/otp/verify", json=payload).status_code == 401


def test_refresh_replay_revokes_family(client, authenticated_farmer):
    old = authenticated_farmer.refresh_token
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": old, "device_id": "phone-1"}).status_code == 200
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": old, "device_id": "phone-1"}).status_code == 401
```

- [x] **Step 2: Run `cd backend; pytest tests/api/test_auth.py -v`**

Expected: FAIL because auth routes are absent.

- [x] **Step 3: Implement authentication services and endpoints**

```python
@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str
    access_expires_in: int


def hash_refresh_token(raw: str, pepper: SecretStr) -> str:
    return hmac.new(
        pepper.get_secret_value().encode(), raw.encode(), hashlib.sha256
    ).hexdigest()
```

Normalize mobile numbers to E.164. Store only OTP HMACs in Redis with five-minute TTL and atomic consume. Rate-limit mobile, IP, and device. Use Argon2id and PyOTP for staff. JWTs contain `sub`, `iss`, `aud`, `iat`, `exp`, `jti`, roles, and assignment path; default lifetime is ten minutes. Refresh sessions store only token hash, device, family, expiry, rotation link, and revocation. Audit every outcome without raw credentials.

- [x] **Step 4: Run `cd backend; pytest tests/api/test_auth.py -v`**

Expected: OTP, staff MFA, logout, expiry, and replay tests pass.

---

### Task 4: Service authorization and PostgreSQL RLS

**Files:**
- Create: `backend/app/services/authorization.py`
- Modify: `backend/app/db/session.py`, `backend/alembic/versions/0001_core_architecture.py`
- Test: `backend/tests/services/test_authorization.py`, `backend/tests/integration/test_rls.py`

**Interfaces:**
- Produces: `authorize(principal, action, resource) -> None`
- Produces: `session_for(principal) -> AsyncIterator[AsyncSession]`

- [x] **Step 1: Write failing scope and direct-SQL isolation tests**

```python
def test_vet_is_denied_outside_assignment(vet_principal, other_district_report):
    with pytest.raises(ForbiddenError):
        authorize(vet_principal, "report.read_identifiable", other_district_report)


@pytest.mark.asyncio
async def test_rls_hides_out_of_scope_report(vet_session, other_district_report):
    assert await vet_session.get(DiseaseReport, other_district_report.id) is None


def test_farmer_reads_owned_report_only(farmer_principal, own_report, other_report):
    authorize(farmer_principal, "report.read", own_report)
    with pytest.raises(ForbiddenError):
        authorize(farmer_principal, "report.read", other_report)
```

- [x] **Step 2: Run `cd backend; pytest tests/services/test_authorization.py tests/integration/test_rls.py -v`**

Expected: policy imports fail and direct SQL exposes the row before RLS exists.

- [x] **Step 3: Implement the policy matrix and transaction-local database context**

```python
async def set_rls_context(session: AsyncSession, principal: CurrentPrincipal) -> None:
    await session.execute(text("select set_config('app.user_id', :v, true)"), {"v": str(principal.user_id)})
    await session.execute(text("select set_config('app.roles', :v, true)"), {"v": ",".join(sorted(r.value for r in principal.roles))})
    await session.execute(text("select set_config('app.location_path', :v, true)"), {"v": principal.location_path or ""})
```

Farmers require ownership. Vets and para-vets require a resource path equal to or below their single assignment. District officers have aggregate actions unless an unexpired audited review grant exists. Force RLS on identifiable tables and use a non-owner, non-`BYPASSRLS` application DB role.

- [x] **Step 4: Run the Task 4 tests again**

Expected: service policies and direct SQL both isolate cross-jurisdiction data.

---

### Task 5: Disease-report persistence and versioned APIs

**Files:**
- Create: `backend/app/schemas/reports.py`, `backend/app/repositories/reports.py`
- Create: `backend/app/services/reports.py`, `backend/app/api/v1/disease_reports.py`
- Modify: `backend/app/api/v1/router.py`
- Test: `backend/tests/api/test_reports.py`

**Interfaces:**
- Produces: create, submit, get, and cursor-paginated list report operations
- Produces: optimistic concurrency through ETag/`If-Match`

- [x] **Step 1: Write failing idempotency, concurrency, and immutability tests**

```python
def test_duplicate_submission_returns_same_report(client, farmer_headers, report_payload):
    headers = {**farmer_headers, "Idempotency-Key": "phone-1:report-7"}
    first = client.post("/api/v1/disease-reports", headers=headers, json=report_payload)
    second = client.post("/api/v1/disease-reports", headers=headers, json=report_payload)
    assert first.status_code == second.status_code == 201
    assert first.json()["data"]["id"] == second.json()["data"]["id"]


def test_stale_version_returns_conflict(client, farmer_headers, draft_report):
    response = client.post(
        f"/api/v1/disease-reports/{draft_report.id}/submit",
        headers={**farmer_headers, "If-Match": '"1"', "Idempotency-Key": "submit-1"},
    )
    assert response.status_code == 409
```

- [x] **Step 2: Run `cd backend; pytest tests/api/test_reports.py -v`**

Expected: route-not-found failures.

- [x] **Step 3: Implement report schemas, transactions, and scoped reads**

```python
class DiseaseReportCreate(BaseModel):
    client_generated_id: UUID
    farm_id: UUID
    animal_id: UUID | None = None
    herd_id: UUID | None = None
    species: Species
    symptoms: list[ReportedSymptom]
    affected_count: int = Field(ge=1)
    mortality_count: int = Field(ge=0)
    onset_date: date
    latitude: Decimal
    longitude: Decimal
    vaccination: VaccinationSnapshot | None = None
    treatment: TreatmentSnapshot | None = None
    environment: EnvironmentSnapshot | None = None
    notes: str | None = Field(default=None, max_length=4000)
```

Validate mortality not exceeding affected count, ownership, and jurisdiction. Freeze the submitted snapshot and its SHA-256 hash. Atomically store the report, audit, idempotency response, and `disease_report.submitted` event. Use `selectinload` for bounded child collections and opaque `(submitted_at, id)` cursors.

- [x] **Step 4: Run `cd backend; pytest tests/api/test_reports.py -v`**

Expected: ownership, idempotency, immutability, pagination, and conflict tests pass.

---

### Task 6: Explainable provider-neutral triage

**Files:**
- Create: `backend/app/risk/contracts.py`, `backend/app/risk/triage.py`
- Create: `backend/app/schemas/decisions.py`, `backend/app/services/decisions.py`, `backend/app/api/v1/decisions.py`
- Modify: `backend/app/api/v1/router.py`
- Test: `backend/tests/services/test_triage.py`, `backend/tests/api/test_decisions.py`

**Interfaces:**
- Produces: `TriageProvider.evaluate(snapshot, rule_pack) -> TriageDecision`
- Produces: `POST /api/v1/disease-reports/{id}/triage`

- [x] **Step 1: Write failing explainability tests**

```python
def test_triage_explains_evidence(severe_report, fmd_rule_pack):
    decision = RuleBasedTriageProvider().evaluate(severe_report, fmd_rule_pack)
    candidate = decision.suspected_diseases[0]
    assert candidate.disease_code == "FMD"
    assert "vesicles" in candidate.contributing_symptoms
    assert "vaccinated_recently" in candidate.negative_evidence
    assert decision.rule_pack_version == "triage-2026.1"
    assert decision.disclaimer == ADVISORY_DISCLAIMER


def test_missing_data_reduces_confidence(severe_report_missing_vaccine, fmd_rule_pack):
    decision = RuleBasedTriageProvider().evaluate(severe_report_missing_vaccine, fmd_rule_pack)
    assert decision.data_confidence < 1.0
    assert "vaccination_status" in decision.missing_fields
```

- [x] **Step 2: Run `cd backend; pytest tests/services/test_triage.py tests/api/test_decisions.py -v`**

Expected: missing contract/provider failures.

- [x] **Step 3: Implement immutable decision contracts and rule evaluation**

```python
ADVISORY_DISCLAIMER = "Advisory only; veterinary assessment is required for diagnosis."


class TriageProvider(Protocol):
    def evaluate(self, snapshot: ReportSnapshot, rule_pack: TriageRulePack) -> TriageDecision: ...


@dataclass(frozen=True, slots=True)
class TriageDecision:
    rule_pack_version: str
    suspected_diseases: tuple[SuspectedDisease, ...]
    contributing_factors: tuple[str, ...]
    missing_fields: tuple[str, ...]
    recommended_actions: tuple[str, ...]
    data_confidence: float
    disclaimer: str = ADVISORY_DISCLAIMER
```

Sum positive evidence, subtract explicit negative evidence, and normalize by possible weight to `[0, 1]`. Rank by normalized score then disease code. Persist snapshot hash, rule version, every match/non-match, score, missing fields, actions, and actor. Replay of `(report_id, snapshot_hash, rule_pack_version)` returns the existing result.

- [x] **Step 4: Run the Task 6 tests again**

Expected: ranking, evidence, uncertainty, persistence, idempotency, and disclaimer tests pass.

---

### Task 7: Risk scoring and automatic veterinary escalation

**Files:**
- Create: `backend/app/risk/scoring.py`
- Modify: `backend/app/services/decisions.py`, `backend/app/api/v1/decisions.py`
- Test: `backend/tests/services/test_risk.py`, `backend/tests/api/test_decisions.py`

**Interfaces:**
- Produces: `RiskScorer.score(snapshot, signals, config) -> RiskDecision`
- Produces: `POST /api/v1/disease-reports/{id}/risk-score`
- Produces: atomic HIGH/CRITICAL veterinary case, alert, audit, and outbox writes

- [x] **Step 1: Write failing boundaries, missing-data, and escalation tests**

```python
@pytest.mark.parametrize(
    ("value", "category"),
    [(0, "LOW"), (30, "LOW"), (31, "MEDIUM"), (60, "MEDIUM"),
     (61, "HIGH"), (80, "HIGH"), (81, "CRITICAL"), (100, "CRITICAL")],
)
def test_risk_boundaries(value, category):
    assert category_for(value).value == category


@pytest.mark.asyncio
async def test_high_risk_opens_case_and_alert(decision_service, high_risk_report):
    decision = await decision_service.score_risk(high_risk_report.id)
    assert decision.category == RiskCategory.HIGH
    assert await case_exists_for(high_risk_report.id)
    assert await alert_exists_for(high_risk_report.id)
```

- [x] **Step 2: Run `cd backend; pytest tests/services/test_risk.py tests/api/test_decisions.py -v`**

Expected: missing scorer and escalation failures.

- [x] **Step 3: Implement contributions and transactional escalation**

```python
@dataclass(frozen=True, slots=True)
class RiskContribution:
    factor: str
    source: str
    normalized_value: Decimal
    weight: Decimal
    points: Decimal


def category_for(value: int) -> RiskCategory:
    if value <= 30: return RiskCategory.LOW
    if value <= 60: return RiskCategory.MEDIUM
    if value <= 80: return RiskCategory.HIGH
    return RiskCategory.CRITICAL
```

Calculate each available factor as `normalized_value * weight * 100`, cap at 100, and round only at the final boundary. Missing data reduces confidence and never contributes zero risk silently. Persist all inputs, sources, weights, contributions, config version, snapshot hash, category, and confidence. HIGH/CRITICAL processing locks the escalation row and creates at most one open case and alert; enqueue outbreak analysis atomically.

- [x] **Step 4: Run the Task 7 tests again**

Expected: boundaries, determinism, contribution, confidence, deduplication, and atomicity pass.

---

### Task 8: Potential-outbreak analysis and controlled declaration

**Files:**
- Create: `backend/app/risk/outbreaks.py`, `backend/app/repositories/surveillance.py`
- Create: `backend/app/services/outbreaks.py`, `backend/app/schemas/outbreaks.py`, `backend/app/api/v1/outbreaks.py`
- Modify: `backend/app/api/v1/router.py`
- Test: `backend/tests/services/test_outbreaks.py`, `backend/tests/api/test_outbreaks.py`

**Interfaces:**
- Produces: `OutbreakAnalyzer.analyze(candidate_reports, baseline, config) -> OutbreakSignal`
- Produces: analyze/list/get and district-officer declare/dismiss APIs

- [x] **Step 1: Write failing cluster, weather, and authority tests**

```python
def test_cluster_creates_potential_signal(analyzer, nearby_similar_reports, baseline):
    signal = analyzer.analyze(nearby_similar_reports, baseline, outbreak_config())
    assert signal.detected is True
    assert signal.state == "POTENTIAL"
    assert {f.name for f in signal.factors} >= {"spatial_cluster", "temporal_cluster"}


def test_weather_alone_never_creates_outbreak(analyzer, one_report, baseline):
    signal = analyzer.analyze(one_report, baseline, outbreak_config(weather_risk=1.0))
    assert signal.detected is False


def test_vet_cannot_declare(client, vet_headers, potential_outbreak):
    response = client.post(
        f"/api/v1/outbreaks/{potential_outbreak.id}/declare",
        headers={**vet_headers, "Idempotency-Key": "declare-1"},
        json={"reason": "Cluster reviewed"},
    )
    assert response.status_code == 403
```

- [x] **Step 2: Run `cd backend; pytest tests/services/test_outbreaks.py tests/api/test_outbreaks.py -v`**

Expected: missing analyzer and route failures.

- [x] **Step 3: Implement configurable analysis and lifecycle commands**

```python
@dataclass(frozen=True, slots=True)
class OutbreakConfig:
    version: str
    radius_km: Decimal
    window_days: int
    minimum_similar_reports: int
    mortality_zscore_threshold: Decimal
    frequency_ratio_threshold: Decimal
```

Use `ST_DWithin` for candidate selection and pure deterministic evaluation for factors. Similar-report count plus spatial/temporal conditions are mandatory; mortality and baseline frequency strengthen the signal. Weather cannot satisfy minimum conditions. Persist memberships, versions, factors, and `POTENTIAL` state. Only an in-jurisdiction district officer may declare/dismiss, with a non-empty reason, lifecycle history, audit, and outbox record.

- [x] **Step 4: Run the Task 8 tests again**

Expected: clustering, baseline, weather limitation, jurisdiction, declaration, dismissal, and replay pass.

---

### Task 9: Public-contract verification and operating documentation

**Files:**
- Create: `backend/README.md`
- Modify: `backend/.env.example`
- Test: `backend/tests/test_openapi.py`, `backend/tests/test_safe_errors.py`

**Interfaces:**
- Produces: complete setup, migration, test, auth, and API instructions.
- Verifies: no secret fields in public schemas and no stack traces in production errors.

- [x] **Step 1: Write failing OpenAPI and safe-error tests**

```python
def test_openapi_documents_security_and_disclaimer(client):
    schema = client.get("/openapi.json").json()
    assert "bearerAuth" in schema["components"]["securitySchemes"]
    triage = schema["paths"]["/api/v1/disease-reports/{report_id}/triage"]["post"]
    assert "Advisory only" in str(triage)


def test_production_error_hides_exception(client, force_internal_error):
    response = client.get("/api/v1/test/internal-error")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "Traceback" not in response.text
    assert "forced secret" not in response.text
```

- [x] **Step 2: Run `cd backend; pytest tests/test_openapi.py tests/test_safe_errors.py -v`**

Expected: FAIL until OpenAPI security and production error mapping are complete.

- [x] **Step 3: Complete OpenAPI, `.env.example`, and README**

Document database/Redis URLs, JWT issuer/audience/keys, refresh pepper, audit key, CORS origins, OTP limits, MFA issuer, and production mode. Include PostgreSQL/PostGIS setup, migration, tests, and Uvicorn startup. Include examples for OTP, staff MFA, report creation, triage, risk, analysis, and officer declaration. Document the advisory limitation and jurisdiction rules.

- [x] **Step 4: Run `cd backend; alembic upgrade head; pytest -q; ruff check .; black --check .`**

Expected: migration, all tests, and static checks pass.

## Plan self-review

- **Spec coverage:** Tasks 2 and 5 cover database/trust; Tasks 1, 3, and 5–9 cover API contracts; Tasks 1, 3, 4, and 9 cover security; Tasks 6–8 cover triage, risk, escalation, and outbreaks.
- **Scope check:** Laboratory processing, vaccination/treatment CRUD, dashboards, file storage, weather-provider integration, worker deployment, and Render packaging remain outside this phase.
- **Placeholder scan:** No prohibited placeholder markers or undefined test steps remain.
- **Type consistency:** `CurrentPrincipal`, snapshot hashes, versions, idempotency claims, and decision results are defined before consumers use them.
