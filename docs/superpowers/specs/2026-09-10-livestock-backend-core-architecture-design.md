# Livestock Health Platform: Core Backend Architecture

**Status:** Approved design baseline

**Date:** 2026-09-10
**Scope:** Database, API, security, and risk/triage architecture only. No application implementation is included in this phase.

## 1. Decisions and boundaries

The platform is a single, government-operated system for Indian livestock health surveillance. It is not multi-tenant. Authorization is based on the authenticated user's role, ownership, and one assigned geographic jurisdiction.

- Farmers are first-class users. They sign in with mobile-number OTP and can manage only their own farms, herds, animals, and submitted reports.
- Staff members use Argon2id password authentication plus TOTP MFA. Staff roles are `PARAVET`, `VETERINARIAN`, `LAB_TECHNICIAN`, `DISTRICT_OFFICER`, and `ADMIN`.
- A staff user has exactly one active geographic assignment. The assignment is not multi-area.
- Veterinarians and para-veterinarians may access identifiable data only within their assignment. District officers receive aggregated surveillance data by default; an explicit, audited case-review grant is required for identifiable records.
- High and critical reports automatically notify the responsible veterinarian and create a veterinary review case. A district officer alone may formally declare or dismiss an outbreak.
- Health records and audit logs are retained indefinitely. The system minimizes collected PII and protects retained data rather than relying on deletion.

The recommended implementation shape is a modular FastAPI monolith. PostgreSQL/PostGIS is the system of record; Redis supports short-lived OTPs, rate limiting, and worker coordination. A transactional outbox communicates committed domain events to notifications, asynchronous analysis, and aggregate projections. This keeps the initial Render deployment simple while retaining clean seams for later service extraction.

## 2. Database architecture

### 2.1 Data principles

PostgreSQL with PostGIS is authoritative for operational data. Domain primary keys use UUIDv7. Timestamps are UTC and each mutable row has `created_at`, `updated_at`, `created_by`, and `updated_by` where applicable. Submitted clinical snapshots, evaluations, alert events, lab results, and audit events are append-only; appropriate operational drafts may be soft-deleted using `deleted_at` and `deleted_by`.

All constraints, indexes, and foreign keys are defined by Alembic migrations. The application uses transactions to make a state change, its audit event, and its outbox record atomic.

### 2.2 Domains and tables

| Domain | Principal tables | Design notes |
|---|---|---|
| Identity and access | `users`, `roles`, `user_roles`, `staff_geographic_assignments`, `auth_identities`, `mfa_credentials`, `sessions`, `otp_challenges` | Mobile identity is normalized to E.164. A partial unique index permits one active assignment per staff user. Refresh-token values and OTP values are stored only as hashes. |
| Geography | `locations`, `veterinary_centers`, `laboratories` | `locations` is a constrained hierarchy: country, state, district, block, village. It stores a geometry and a materialized hierarchy path for fast descendant queries. Parent/child levels are validated. |
| Farm and animal records | `farms`, `herds`, `animals` | Farms belong to a farmer and location; herds belong to farms; animals belong to a farm and optionally a herd. Ownership and location history are modeled explicitly when transfers are required. |
| Clinical master data | `diseases`, `symptoms`, `disease_symptoms`, `risk_rule_packs`, `triage_rule_packs` | Disease, symptom, and rule content are versioned reference data with central administrative governance. |
| Reporting | `disease_reports`, `disease_report_symptoms`, `report_vaccination_snapshots`, `report_treatment_snapshots`, `report_environment_snapshots`, `attachments` | A report may concern an animal or herd and retains all submitted clinical/context data as an immutable snapshot after submission. |
| Clinical workflow | `veterinary_cases`, `case_transitions`, `treatments`, `vaccinations`, `laboratory_samples`, `laboratory_results` | State transitions are modeled as explicit commands and history rows, not arbitrary status edits. |
| Decisions and surveillance | `triage_results`, `triage_findings`, `risk_scores`, `risk_factor_contributions`, `outbreaks`, `outbreak_report_memberships`, `alerts`, `notifications`, `weather_records` | Every machine-assisted decision references source data and rule/configuration version. |
| Trust and delivery | `audit_logs`, `sync_receipts`, `outbox_events`, `dashboard_aggregates` | Audit entries are append-only and hash-chained. Sync receipts enforce replay-safe offline submissions. Aggregates are rebuildable read models. |

### 2.3 Integrity, location, and performance

Clinical counts have non-negative checks, submission/case/lab lifecycles have valid-transition constraints, and references cannot be orphaned. Disease-report duplicate prevention uses a unique key on `(reporter_id, client_generated_id)`. `sync_receipts` stores request fingerprint, server result, and acknowledgement state so a replay returns the original accepted/conflict result.

Indexes cover location hierarchy path; PostGIS geometry; report status, onset/submission date, disease, species, and risk level; active veterinary/laboratory queues; owner/farm/animal lookup; vaccination due date; and bounded time-window surveillance queries. Reporting screens use cursor pagination and precomputed aggregates instead of N+1 relationships or unbounded joins.

## 3. API architecture

### 3.1 Layering

FastAPI routes are versioned under `/api/v1`. Route handlers validate Pydantic contracts and delegate to application services. Services authorize actions, apply workflow rules, open transactions, and emit domain events. Repositories are the only persistence boundary. This separates the external API from persistence and allows the rule engine to evolve independently.

All APIs return a stable JSON envelope:

```json
{
  "data": {},
  "meta": {"request_id": "..."},
  "error": null
}
```

Failures instead return a stable machine-readable `error.code`, a safe user-facing message, and the request ID. Production responses never contain stack traces, SQL messages, tokens, password values, secrets, or internal policy details.

### 3.2 API behavior

- Cursor pagination and bounded filters apply to high-volume lists and dashboard drill-downs.
- Every mutation supplies an idempotency key. Offline clients also send a `client_generated_id`, entity version, and client timestamps.
- Mutable resources use optimistic concurrency through version/ETag checks. A stale change receives `409 CONFLICT` with a safe reconciliation payload.
- Authorization is action-based and scope-aware in the service layer. District-officer dashboard endpoints return aggregates by default.
- Asynchronous effects return `202 ACCEPTED` where processing is deferred. The state transition itself, audit event, and outbox event remain atomic.

### 3.3 Resource groups

| Group | Core responsibilities |
|---|---|
| `/auth` | Farmer OTP request/verify; staff password login and MFA challenge/verify; refresh, logout, session management, and `/me`. |
| `/farms`, `/herds`, `/animals`, `/vaccinations`, `/treatments` | Scoped health-record management. |
| `/disease-reports` | Draft, submission, detail/query, secure attachments, and advisory triage command. Submission freezes the clinical snapshot. |
| `/cases`, `/lab/samples`, `/lab/results` | Explicit review, referral, collection, processing, validation, and closure transitions. |
| `/risk`, `/outbreaks`, `/alerts`, `/risk-map`, `/dashboard` | Read models and controlled analysis/declaration commands. |
| `/sync` | Replay-safe offline batch synchronization with per-item accepted, conflict, or retry results. |
| `/health`, `/health/ready` | Render liveness and dependency readiness. |

OpenAPI documents schema validation, role requirements, conflict/idempotency behavior, error cases, and the non-diagnostic triage disclaimer.

## 4. Security architecture

### 4.1 Identity and session security

Farmer OTP values are salted hashes in Redis, expire quickly, are single use, and are rate-limited by normalized mobile number, IP, device, and time window. Staff passwords use Argon2id. Staff MFA uses TOTP, with hashed one-time recovery codes.

Access JWTs are short-lived, issuer/audience-bound, and signed with keyed secret material identified by `kid`. Refresh tokens are opaque, stored only as hashes, bound to a session/device, rotated at every use, and organized into token families. Refresh-token replay revokes the family. All keys are injected through secret management/environment configuration, never source control; rotation is supported.

### 4.2 Authorization and data protection

The service layer enforces role, action, ownership, geographic assignment, and explicit case-review grants. PostgreSQL Row-Level Security provides defense in depth: each request transaction sets the authenticated actor, roles, and jurisdiction as transaction-local database settings, and policies reject rows outside that scope. Farmer records are owner-only. Para-vets and vets are restricted to their sole assignment. District officers receive de-identified aggregate data unless granted audited review access.

Dedicated least-privilege database roles are used for migrations, runtime application operations, background workers, and reporting. SQLAlchemy parameterization, Pydantic validation, bounded query inputs, and no dynamic SQL prevent injection and abuse.

### 4.3 Platform and upload controls

Production requires TLS and explicit CORS origins. The application sets HSTS, CSP, anti-framing, MIME-sniffing, referrer, and safe cache headers. Request size limits, endpoint/IP/account rate limits, request IDs, and safe error mapping apply consistently.

Upload processing validates size, allow-listed extension, server-derived MIME type, and file magic bytes; it replaces source filenames, malware-scans content, stores objects encrypted outside the application filesystem, and serves them only with authorization-checked, short-lived signed URLs. Uploaded content is never executed.

PII, backups, and object storage are encrypted at rest. Logs redact secrets, tokens, passwords, OTPs, phone numbers, and unnecessary precise coordinates. Audit log rows include actor, action, target, request metadata, result, timestamp, and chained hash; periodic signed hashes are anchored outside the primary database to detect tampering. Authentication, authorization, and sensitive mutation events are audited transactionally.

## 5. Risk and triage architecture

### 5.1 Explainable advisory triage

`TriageProvider` is the stable application interface. Its initial implementation evaluates a centrally governed, versioned rule pack. Inputs are the immutable submitted report snapshot: species, symptom combinations, severity, onset, affected/mortality counts, vaccination context, environmental context, and exclusion signals.

Output ranks suspected conditions with likelihood bands, matched and unmatched evidence, uncertainty, and recommended next actions. It must state clearly that it is advisory and not a definitive veterinary diagnosis. The service cannot prescribe treatment, close a case, or declare an outbreak. A veterinarian may supersede it only by recording a reason in a new immutable review result.

Each `triage_result` stores the input snapshot hash, rule-pack version, per-rule matches, positive and negative evidence, raw and normalized scores, recommended-action source, invoking actor, and timestamp. A future ML scorer can operate behind the same provider contract without changing public response shapes.

### 5.2 Configured 0-100 risk score

Risk is separately calculated and versioned. It produces a deterministic score and category: LOW 0-30, MEDIUM 31-60, HIGH 61-80, CRITICAL 81-100. Factors are normalized, weighted, and retained individually:

- clinical severity: symptoms, affected proportion, mortality;
- exposure and context: vaccination coverage, weather/environment anomaly;
- surveillance: local similar reports and historical baseline;
- spatial-temporal patterns: proximity, timing, and cluster density;
- confidence/data quality: report completeness, verification, and contradictions.

Missing information lowers confidence and prompts follow-up; it never silently reduces risk. `risk_scores` and `risk_factor_contributions` store factor value, source, normalization, weight, contribution, rule-pack version, and final confidence.

### 5.3 Escalation and outbreaks

HIGH and CRITICAL scores create alerts, route a veterinary review case, notify the responsible veterinarian, and schedule separate outbreak analysis. Outbreak analysis evaluates versioned thresholds for spatial radius, time window, report count, disease similarity, mortality anomaly, report-frequency anomaly, and local historical baseline. It may create a `POTENTIAL_OUTBREAK` only. A district officer must review and formally declare or dismiss it, with a reason recorded in immutable history.

Weather can influence a risk factor but cannot independently create a disease or outbreak declaration. All triage/risk/outbreak decision requests are idempotent and preserve source and configuration versions for reproducibility.

## 6. Non-functional acceptance criteria for this phase

- All identified records and workflows have ownership, jurisdiction, and lifecycle rules.
- Every automated conclusion is reproducible from persisted source inputs and configuration version.
- Duplicate offline report delivery creates no duplicate clinical record or downstream escalation.
- Privileged access is independently blocked by API policy and database RLS.
- Government surveillance works without exposing unnecessary farmer PII.
- The system can run as a modular monolith on Render and preserve later extraction seams through services and transactional outbox events.

## 7. Explicitly deferred

This design does not implement routes, database models, migrations, UI flows, external SMS/weather/object-storage vendors, ML models, deployment files, or tests. Those will be addressed only in subsequent approved implementation planning.
