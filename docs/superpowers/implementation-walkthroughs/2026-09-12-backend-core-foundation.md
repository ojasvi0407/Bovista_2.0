# Backend core foundation implementation walkthrough

This file preserves the implementation context for later Bovista work. The foundation now
includes the database, API, security, risk/triage, clinical, laboratory, alert,
surveillance-dashboard, governance, and deployment architecture.

## Agreed operating model

- One government-operated system for farmers and government staff.
- Farmers authenticate with a normalized mobile number and single-use OTP.
- Staff authenticate with Argon2id password plus encrypted-seed TOTP MFA.
- Each staff account has one active geographic assignment.
- Veterinarians and para-veterinarians can access identifiable livestock records only
  under their assigned hierarchy path.
- District officers receive aggregate access by default; identifiable review requires an
  active, expiring case grant.
- HIGH and CRITICAL risk automatically create a veterinary case and alert.
- Automated analysis creates only `POTENTIAL`; a district officer alone can declare or
  dismiss an outbreak.
- Domain records and audit history are retention-oriented, with no ordinary hard-delete
  API.

## Implementation sequence

1. Created the FastAPI shell, stable response envelopes, request IDs, CORS allowlisting,
   security headers, and safe production exception mapping.
2. Installed and verified PostgreSQL 16 plus PostGIS 3.6 locally, then created an isolated
   `bovista_test` database role with no superuser or RLS-bypass privilege.
3. Added UUIDv7-compatible identifiers, UTC timestamps, normalized domain tables,
   PostGIS geometry/indexes, Alembic migrations, HMAC-chained audit records,
   transactional outbox events, and idempotency receipts.
4. Added farmer OTP, staff password/TOTP, JWT access claims, opaque refresh rotation,
   replay-family revocation, logout, and `/me`.
5. Added service authorization plus transaction-local forced PostgreSQL RLS across the
   identifiable livestock graph. Authenticated HTTP dependencies establish RLS context.
6. Added ownership-checked, idempotent disease-report creation; version/ETag submission;
   complete canonical snapshot hashing; and database triggers that freeze submitted
   reports, symptoms, context, and attachments.
7. Added provider-neutral explainable triage contracts and deterministic 0–100 risk
   scoring with explicit missing inputs, confidence, factor provenance, automatic case
   routing, alerts, notification/outbreak outbox events, and replay-safe persistence.
8. Added deterministic outbreak clustering. The HTTP boundary accepts only a trusted seed
   report; server-controlled settings and candidate evidence are derived internally, with
   report candidates sourced from PostgreSQL/PostGIS. Lifecycle transitions require an
   in-scope district officer and a reason.
9. Added OpenAPI security/disclaimer checks, production-safe error tests, and operating
   instructions in `backend/README.md`.
10. Hardened production configuration, generic error handling, request-size limits,
    request IDs, OTP gateway delivery, current database-backed role checks, staff lockout,
    persisted single-use MFA challenges, and bounded report/animal queries.
11. Added recipient/owner-scoped cursor-paginated alerts with replay-safe acknowledgement,
    audit, and outbox writes. Added district/admin aggregate dashboards scoped by geographic
    hierarchy and filterable/groupable by date, location, species, and suspected disease.
12. Added normalized vaccination and laboratory-sample persistence needed by dashboard
    metrics, forced RLS for both tables, immutable vaccination records, migration `0007`,
    a non-root container, Render Blueprint, and local PostGIS/Redis Compose stack.
13. Completed scoped farm, herd, and cursor-paginated animal CRUD with version conflicts,
    retention-safe archives, parent-child guards, audit entries, and outbox events.
14. Added immutable vaccination and treatment command APIs, explicit reversal history,
    corrected due-dose selection, clinical indexes, service authorization, and forced RLS.
15. Added the fixed laboratory lifecycle with immutable transition/result history,
    role-specific commands, result alerts, and case closure guards. Added explicit
    veterinary case review, referral, resume, close, and history APIs.
16. Added governed location, disease, symptom, triage-pack, and risk-pack administration;
    published rule and audit history is database-protected from update and deletion.
17. Added bounded MFA attempts, secure staff provisioning, a durable outbox worker with
    internal outbreak analysis and HTTPS delivery, migrations through `0012`, CI with a
    real PostGIS runtime role, and a Render background-worker definition.

## Verification checkpoint

On 2026-09-13, the pre-push suite reported 96 passing tests before the final documentation
contract additions. Alembic upgraded an empty database through `0012`, and `alembic check`
reported no pending operations. PostgreSQL reported PostGIS, 21 forced-RLS domain tables,
four frozen report-snapshot triggers, eight clinical/audit/rule-history triggers, both
workflow transition triggers, and a runtime role without superuser or RLS-bypass
privileges. Direct database mutation of vaccination, audit, and rule-pack history was
rejected. The final verification result and pushed commit are recorded in the delivery
summary for this implementation run.

## Next hardening work

Before a production pilot, add staff MFA IP/device rate limits, historical surveillance
baselines, key IDs and rotation, backup/restore drills, and production observability.
Operators must configure the government SMS and event gateways, Redis, Render secrets,
the worker service account, and deployment-specific incident-response controls.
