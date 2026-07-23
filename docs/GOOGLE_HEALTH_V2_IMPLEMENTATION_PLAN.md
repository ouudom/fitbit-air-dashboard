# Google Health V2 implementation plan

Status: approved design, implementation not started.

Primary design references:

- [`DATABASE.dbml`](./DATABASE.dbml)
- [`GOOGLE_HEALTH_SYNC_DESIGN.md`](./GOOGLE_HEALTH_SYNC_DESIGN.md)
- [`GOOGLE_HEALTH_DATA_TYPES.md`](./GOOGLE_HEALTH_DATA_TYPES.md)
- [Google Health API data types](https://developers.google.com/health/data-types)
- [Google Health OAuth scopes](https://developers.google.com/health/scopes)
- [Google Health webhooks](https://developers.google.com/health/webhooks)

## 1. Objective

Deliver a backend-first Google Health ingestion platform that:

- Connects one LifeStats user to one Google Health identity.
- Polls all 39 current Google Health data types by default.
- Receives supported Google Health webhook notifications.
- Stores complete returned items plus common query fields.
- Uses Google Health as authoritative source.
- Keeps local health rows rebuildable.
- Stores physical timestamps as UTC.
- Supports configurable per-type polling without code changes.
- Runs without frontend feature dependencies.
- Enables later data APIs and frontend work.

## 2. Locked decisions

- All 39 data types are enabled by default.
- Scheduled polling pauses from 00:00 through 05:59 user-local time.
- Manual sync bypasses quiet hours.
- Webhook-triggered sync bypasses quiet hours.
- Dispatcher runs every five minutes.
- OAuth state lives in Redis with a 10-minute TTL and atomic consumption.
- LifeStats does not duplicate the scope list in its UI.
- Google OAuth consent still displays the requested permissions.
- Freshness is stored but not displayed.
- `users.timezone` stores an IANA timezone.
- Physical timestamps use UTC `timestamptz`.
- Daily records retain Google's civil date.
- Reconcile is preferred over raw-source list.
- Raw payload remains with the record.
- Missing Google records are soft-deleted for 30 days.
- Disconnect retains cached data.
- Cache deletion is a separate explicit destructive action.
- Polling is implemented and validated before webhook activation.
- Backend sync ships before data-product and frontend expansion.

## 3. Safety and database cutover

The intended deployment uses a fresh database. Do not automate deletion of the
old database.

Safe cutover:

1. Stop API writes, workers, and scheduler.
2. Back up old PostgreSQL database.
3. Verify backup restoration in an isolated PostgreSQL instance.
4. Preserve `.env`, encryption keys, Google credentials, and old container image.
5. Create a new database or new PostgreSQL volume.
6. Run the complete Alembic migration chain against the empty database.
7. Validate schema and application startup.
8. Switch LifeStats to the new database.
9. Recreate the local account and reconnect Google Health.
10. Run initial sync and verify results.
11. Keep old database through an explicit rollback window.
12. User may retire the old database manually after acceptance.

Historical migrations remain immutable. New work uses additive Alembic
migrations. A fresh database may still contain protected historical tables
created by the migration chain; runtime ignores them.

No implementation command should drop a database, volume, table, or historical
migration.

## 4. Target database schema

### Application tables

#### `users`

Add:

```text
timezone varchar(64) not null
```

Default for current installation: `Asia/Phnom_Penh`.

Validation:

- Must resolve as an IANA timezone.
- API serializes timestamps as UTC.
- Frontend converts event timestamps using `users.timezone`.

#### `sessions`

Replace runtime use of `app_sessions`.

Required behavior:

- Hashed session token.
- Hashed CSRF token.
- Expiry.
- Optional revocation and last-seen timestamps.
- User agent and IP metadata.

Historical `app_sessions` remains protected until rollback ends.

### Google Health tables

#### `gh_connections`

Stores:

- User ownership.
- Stable Google Health user ID.
- Encrypted access and refresh tokens.
- Token expiry.
- Granted scopes.
- Connection state and verification timestamps.

One active connection per user.

#### `gh_sync_job`

Primary key:

```text
(connection_id, data_type, fetch_method)
```

Stores:

- Enabled flag.
- Poll interval.
- Initial lookback.
- Incremental overlap.
- Page size.
- Priority.
- Next poll time.
- Current status.
- Active query window.
- Page token.
- Lease expiry.
- Consecutive failures.
- Record count.
- Last attempted/succeeded timestamps.
- Last error.

Seed one or more rows for every supported data type when a connection is
created. All rows default enabled when their OAuth scope was granted.

#### `gh_records`

Stores every returned point or rollup:

- Connection.
- Data type.
- Record type.
- Fetch method.
- Provider name when present.
- Stable identity hash.
- Payload hash.
- Civil record date.
- UTC start/end timestamps.
- Source family.
- Complete returned item in `raw_payload`.
- Provider timestamps.
- First/last sync timestamps.
- Soft-delete timestamp.

Idempotency key:

```text
(connection_id, data_type, fetch_method, identity_hash)
```

Do not store the surrounding page response. Persist individual returned items.
Page token lives temporarily in `gh_sync_job`.

#### `gh_webhook_events`

Add:

- Local UUID.
- Connection when resolved.
- Provider user ID.
- Subscription name.
- Data type IDs.
- Operation.
- Physical/civil intervals.
- Canonical event hash with unique constraint.
- Complete raw request body.
- Signature-verification result.
- Processing status.
- Error.
- Received/processed timestamps.

The event hash supplies retry deduplication when Google redelivers.

## 5. Migration implementation

Create additive migration:

```text
2026xxxx_0002_google_health_v2
```

Migration responsibilities:

1. Add `users.timezone`.
2. Create `sessions`.
3. Create `gh_connections`.
4. Create `gh_sync_job`.
5. Create `gh_records`.
6. Create `gh_webhook_events`.
7. Add foreign keys and indexes.
8. Copy compatible active session/connection data when present.
9. Leave legacy tables untouched.
10. Provide non-destructive downgrade.

Migration tests:

- Empty PostgreSQL database upgrades from zero to head.
- Legacy PostgreSQL snapshot upgrades to head.
- Existing user and health history remains unchanged.
- Running upgrade twice is safe.
- New foreign keys and indexes exist.
- Downgrade does not remove health history.

The production Docker image must not start workers or scheduler until migration
success and API health.

## 6. OAuth implementation

### Requested read scopes

Request only current read requirements:

```text
googlehealth.activity_and_fitness.readonly
googlehealth.health_metrics_and_measurements.readonly
googlehealth.nutrition.readonly
googlehealth.sleep.readonly
googlehealth.ecg.readonly
googlehealth.irn.readonly
googlehealth.location.readonly
```

Do not request write-only, profile, or settings scopes until a feature needs
them.

Handle partial consent:

- Save actual granted scopes.
- Enable only data types covered by granted scopes.
- Keep ungranted types disabled with a machine-readable reason.
- Connection remains usable when some scopes are declined.

No custom scope list appears in LifeStats UI. Google's consent screen remains
authoritative and unavoidable.

### OAuth state

Keep implemented Redis design:

```text
lifestats:google-health:oauth-state:{sha256(state)}
```

- Value: LifeStats user ID.
- TTL: 10 minutes.
- Callback: atomic `GETDEL`.
- Redis failure: fail closed.

## 7. Data-type registry

Create a version-controlled registry under `modules/google_health`.

Every one of 39 types defines:

```text
endpoint ID
payload union field
record kind
OAuth scope
preferred fetch method
supported operations
filter field
page size
maximum range
polling tier
initial lookback
incremental overlap
webhook support
true-zero behavior
```

Startup validation:

- Exactly 39 known types.
- Unique endpoint IDs.
- Fetch method supported by official capability.
- Page size within API limit.
- Sleep/exercise page size no greater than 25.
- Four constrained types use maximum 14-day ranges.
- Other types use maximum 90-day ranges.

Registry changes require fixtures and tests.

## 8. Fetch strategy

Preferred read behavior:

- Use `reconcile` for the logical product stream when supported.
- Use `list` for ECG, irregular rhythm, food, food measurement units, or
  source diagnostics.
- Use `dailyRollUp` for rollup-only daily types.
- Use `rollUp` only for explicitly required physical-window aggregates.
- Do not poll list and reconcile for the same type by default.

Pagination:

- Sleep/exercise: 25.
- Other list/reconcile types: initially 1,000.
- Continue until token absent.
- Save token only after successfully committing the page.

Range splitting:

- Heart rate, active minutes, total calories, and calories in heart-rate zone:
  maximum 14 days.
- All others: maximum 90 days.

## 9. Normalization and record identity

For each returned item:

1. Preserve complete item as JSONB.
2. Extract provider name.
3. Extract UTC start/end timestamp.
4. Extract Google civil date.
5. Extract source family.
6. Canonicalize JSON for hashing.
7. Compute `payload_hash`.
8. Compute deterministic `identity_hash`.
9. Upsert transactionally.
10. Clear `deleted_at` if record reappears.

Identity rules:

- Identifiable point: provider resource name.
- Daily point: connection, data type, civil date, source identity.
- Interval/sample without name: data type, source identity, physical time/window.
- Rollup: data type, fetch method, source family, aggregation window.

Never use payload content alone as identity. A corrected value should update the
same record.

## 10. Polling implementation

### Dispatcher

Replace fixed `sync_all` schedule with dispatcher every five minutes.

Select:

```sql
WHERE enabled
  AND next_poll_at <= now()
  AND (lease_until IS NULL OR lease_until < now())
ORDER BY priority, next_poll_at
FOR UPDATE SKIP LOCKED
```

Claim a bounded batch. Set lease. Queue one worker task per state row.

### Quiet hours

Use `users.timezone`.

```text
quiet: 00:00 inclusive to 06:00 exclusive
```

Scheduled polling:

- Defers to 06:00 plus 0–10 minute jitter.
- Overdue work collapses into one current sync, not one job per missed interval.

Manual and webhook-triggered sync:

- Run immediately.
- Bypass quiet hours.

### Default tiers

| Tier | Interval | Initial history | Overlap |
| --- | ---: | ---: | ---: |
| Steps, heart rate, activity | 15 min | 90 days | 2 hours |
| Exercise, sleep, nutrition, hydration | 30 min | 90 days | 7 days |
| Measurements | 60 min | 90 days | 7 days |
| Daily-derived values | Daily after 06:10 | 90 days | 14 days |
| ECG, IRN, food catalogs, height | 6 hours | 90 days | 30 days |

Daily types receive one noon retry when morning data is not yet available.

### Initial sync

After Google connection:

1. Seed all 39 type schedules.
2. Disable only types without granted scope.
3. Queue initial 90-day backfill by priority.
4. Process activity and dashboard-critical types first.
5. Continue remaining types without blocking application startup.
6. Expose backend sync status endpoint.
7. Do not require frontend work for completion.

Deeper history is a later explicit backfill operation.

## 11. Retry and failure handling

Per request:

- Refresh access token once on `401`.
- Mark authorization expired if refresh fails.
- Honor `Retry-After` on `429`.
- Retry network errors, `408`, `429`, and `5xx`.
- Do not retry ordinary permission or validation `4xx`.
- Full-jitter exponential backoff.
- Base one second.
- Cap 60 seconds.
- Maximum five attempts in one worker execution.

After worker exhaustion:

```text
failure 1: approximately 5 minutes
failure 2: approximately 15 minutes
failure 3: approximately 1 hour
failure 4+: approximately 6 hours
```

Clear failure count after complete success.

Lease recovery:

- Expired lease makes state eligible again.
- Upserts remain idempotent.
- Partial pages never trigger deletion.

## 12. Reconciliation and deletion

Only mark missing rows deleted after:

- Complete successful pagination.
- Complete successful requested window.
- Authoritative reconcile/list semantics for that type.

Webhook `DELETE`:

1. Persist notification.
2. Fetch/reconcile supplied interval immediately.
3. Confirm absence.
4. Set `deleted_at`.

Retention:

- Soft-deleted rows: 30 days.
- Restore if Google returns them again.
- Hard-purge after retention.
- Never infer zero from absence unless the type supports true zeros.

## 13. Raw payload retention

Compact V2 depends on `raw_payload`.

Policy:

- Retain raw payload for active record lifetime.
- Retain through 30-day soft-delete window.
- Encrypt PostgreSQL storage and backups.
- Redact health payloads and tokens from application logs.
- Use PostgreSQL TOAST compression initially.

Later, if typed subtype tables exist:

- Keep successful raw payload at least 90 days.
- Keep normalization failures until repaired.
- Preserve hash and provider identity after payload expiration.

## 14. ECG and heart-rate storage

Heart rate:

- Store UTC timestamp and common identity columns.
- Store exact item JSONB.
- Use composite indexes from V2 schema.
- Measure database and index growth.
- Add monthly partitioning only after real volume justifies it.

ECG:

- Store metadata and raw payload initially.
- Never create one database row per waveform sample.
- Track payload size.
- If payload/backups exceed agreed threshold, move waveform bytes to encrypted
  object storage.
- PostgreSQL then keeps object key, checksum, byte size, and metadata.

Suggested review thresholds:

- Any individual payload greater than 256 KiB.
- `gh_records` or indexes growing faster than available backup/storage budget.
- Backup or restore time exceeding deployment objective.

## 15. Webhook implementation

### Configuration

Add environment values:

```text
GOOGLE_CLOUD_PROJECT_NUMBER
GOOGLE_HEALTH_SUBSCRIBER_ID
GOOGLE_HEALTH_WEBHOOK_URL
GOOGLE_HEALTH_WEBHOOK_AUTH_SECRET
GOOGLE_HEALTH_WEBHOOK_ENABLED
```

Use a Google Cloud service account with least-privilege Google Health subscriber
management role. Prefer workload identity/ADC over static service-account keys.

### Receiver

Add:

```http
POST /api/v1/webhooks/google-health
```

Requirements:

- Public HTTPS TLS 1.2+ endpoint.
- Read raw body before JSON parsing.
- Verify configured Authorization header.
- Verify `GOOGLE-HEALTH-API-SIGNATURE`.
- Cache Google's rotating public keyset with bounded TTL.
- Reject missing/invalid authorization or signature.
- Support Google's authorized/unauthorized verification handshake.
- Insert deduplicated `gh_webhook_events` row.
- Return `204 No Content` immediately.
- Queue processing after durable insert.

### Subscriber

Add an explicit management command, not automatic API startup mutation:

```text
google-health-subscriber apply
google-health-subscriber inspect
```

`apply`:

- Creates or patches subscriber.
- Uses complete supported webhook type configuration.
- Uses automatic subscriptions where supported.
- Performs endpoint verification.
- Reads back subscriber state.

### Processing

Worker:

1. Resolve connection by `healthUserId`.
2. Read operation and intervals.
3. Queue immediate per-type fetch.
4. Bypass quiet hours.
5. Process UPSERT and DELETE idempotently.
6. Mark event complete or failed.

Webhooks do not replace polling:

- No webhook backfill.
- Not all data types support notifications.
- Retried notifications can duplicate.
- Daily reconciliation sweep remains enabled.

### Webhook activation gate

Do not register production subscriber until:

- All-type polling passes.
- Idempotency passes.
- Interval fetch passes.
- Signature verification passes.
- Verification handshake passes.
- Receiver returns `204` within latency budget.
- Daily reconciliation recovery passes.

## 16. Disconnect and cache deletion

Disconnect:

1. Revoke Google token when supported.
2. Delete local encrypted tokens.
3. Mark connection revoked.
4. Disable all sync jobs.
5. Preserve cached records.
6. Preserve connection status for UI.

Separate cache deletion action:

- Exact preview and explicit confirmation.
- Delete only selected user's rebuildable Google cache.
- Preserve application user/session unless separately requested.
- Record action in audit logs without health payload.

## 17. API surface

Backend-first endpoints:

```text
GET  /api/v1/integrations/google-health
GET  /api/v1/integrations/google-health/connect
POST /api/v1/integrations/google-health/disconnect
POST /api/v1/sync
GET  /api/v1/sync
GET  /api/v1/sync/{data_type}
POST /api/v1/sync/{data_type}
POST /api/v1/webhooks/google-health
```

Manual sync supports:

- One type.
- Selected types.
- All enabled types.
- Optional bounded date range.

Manual sync bypasses quiet hours but still respects API range and rate limits.

No frontend dependency. OpenAPI contract generated and checked.

## 18. Observability

Structured logs:

- Connection ID.
- Data type.
- Fetch method.
- Window.
- Page count.
- Request count.
- Fetched/upserted/deleted counts.
- Duration.
- Retry count.
- Sanitized error class.

Never log:

- Access/refresh tokens.
- OAuth codes.
- OAuth state.
- Raw health payloads.
- Webhook authorization secret.

Metrics:

- Sync success/failure by type.
- Last success age.
- Due/leased state count.
- API status and `429` count.
- Records and bytes by type.
- Webhook accepted/rejected/duplicate/failed count.
- Webhook processing latency.
- Database growth.

## 19. Test plan

### Unit

- Registry contains all 39 types.
- Scope-to-type mapping.
- Fetch-method selection.
- Filter generation.
- 14-day and 90-day chunking.
- Pagination.
- UTC/civil-date parsing.
- Identity and payload hashing.
- Quiet-hour calculation by IANA timezone.
- Manual/webhook quiet-hour bypass.
- Retry classification and jitter.
- True-zero versus absence.
- Soft-delete and restore.
- Webhook event hash.
- Signature verification.

### Integration

- Redis OAuth state one-time behavior.
- PostgreSQL idempotent upsert.
- `FOR UPDATE SKIP LOCKED` leasing.
- Lease recovery.
- Partial-page crash recovery.
- Empty and legacy migrations.
- Initial 39-type state seeding.
- OAuth partial consent.
- Webhook handshake.
- Webhook duplicate delivery.
- UPSERT/DELETE interval processing.
- Disconnect retains cache.

### End-to-end

- Fresh database setup.
- Create private account.
- Connect Google Health.
- Complete initial 90-day sync.
- Scheduled polling skips 00:00–06:00.
- Manual sync runs during quiet hours.
- Webhook sync runs during quiet hours.
- Restart API/worker/scheduler mid-sync.
- Resume without duplicate records.
- Reconnect after token revocation.

## 20. Deployment and fresh initialization

### Pre-deployment

1. Complete all quality gates.
2. Build Docker images.
3. Test empty PostgreSQL migration.
4. Test legacy PostgreSQL migration.
5. Verify Redis persistence and health.
6. Verify Google Cloud scopes.
7. Verify webhook service account and IAM.
8. Verify public HTTPS callback and webhook URLs.
9. Take and restore old-database backup.

### Fresh database initialization

Use a new database name or new volume while old database remains intact.

Sequence:

1. Stop API, worker, scheduler, and web.
2. Start only PostgreSQL and Redis.
3. Create fresh database.
4. Point `DATABASE_URL` to fresh database.
5. Run `uv run alembic upgrade head`.
6. Verify `alembic current` equals head.
7. Inspect required V2 tables and indexes.
8. Start API only.
9. Verify `/healthz` and OpenAPI.
10. Complete private account setup.
11. Connect Google Health and grant desired scopes.
12. Verify 39 sync-state rows or covered fetch-state set.
13. Start worker.
14. Trigger initial sync.
15. Observe initial priority types.
16. Start scheduler.
17. Verify quiet-hour and next-poll calculations.
18. Start web and proxy.
19. Validate same-origin application flow.
20. Keep webhook disabled until activation gate passes.

### Webhook activation

1. Deploy verified receiver.
2. Enable webhook configuration.
3. Run subscriber `inspect`.
4. Run subscriber `apply`.
5. Confirm two-step verification handshake.
6. Send/test real data change.
7. Confirm durable event, `204`, worker fetch, and record upsert.
8. Confirm duplicate notification does not duplicate records.
9. Keep daily reconciliation sweep.

### Rollback

- Stop new stack.
- Restore previous `DATABASE_URL`, `.env`, and image.
- Start old stack against preserved old database.
- Do not downgrade or mutate old health history.

### Old database retirement

Not automated by this plan.

After explicit acceptance and rollback-window completion:

1. Verify fresh backup of new database.
2. Verify restoration of new backup.
3. Verify Google reconnection and sync completeness.
4. Verify no rollback need remains.
5. User may manually retire old database/volume.

## 21. Quality gates

Required:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
npm run lint
npm run typecheck
npm run build
npm run openapi:check
docker compose build
```

Production-only:

- Empty PostgreSQL migration test.
- Legacy PostgreSQL migration test.
- Redis integration test.
- Webhook signature fixture test.
- Webhook handshake test.
- Docker health and restart test.
- Database backup/restore test.

## 22. Implementation order

### Milestone 1: V2 schema and migration

- Add migrations and ORM models.
- Add timezone.
- Add migration tests.
- No polling cutover yet.

Exit: empty/legacy migrations pass.

### Milestone 2: generic all-type ingestion

- Registry.
- Fetch strategies.
- UTC/civil parsing.
- Generic record persistence.
- Identity hashing.
- Initial backfill.

Exit: all 39 types exercised with fixtures; supported scopes sync.

### Milestone 3: flexible polling

- Dispatcher.
- Leases.
- Quiet hours.
- Manual bypass.
- Retry/backoff.
- Soft deletion.

Exit: restart-safe polling passes multi-worker tests.

### Milestone 4: webhook receiver

- Receiver.
- Authentication/signature verification.
- Durable inbox.
- Event worker.
- Subscriber management command.

Exit: verification, duplicate delivery, UPSERT, DELETE, and nighttime bypass pass.

### Milestone 5: fresh deployment

- Backup/restore drill.
- Fresh database migration.
- Google reconnection.
- Initial sync.
- Polling activation.
- Webhook activation.

Exit: stable backend sync and observability.

### Milestone 6: later product work

After backend acceptance:

- Add typed query services or projections.
- Add Fitness, Sleep, and Health APIs.
- Build frontend pages.
- Add Google-first write features only with required write scopes.

Do not block backend sync deployment on these later features.
