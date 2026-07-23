# Google Health full-sync design

Verified against Google Health API v4 documentation on 2026-07-23.

Primary references:

- [Data-type catalog](https://developers.google.com/health/data-types)
- [DataPoint resource and methods](https://developers.google.com/health/reference/rest/v4/users.dataTypes.dataPoints)
- [List](https://developers.google.com/health/reference/rest/v4/users.dataTypes.dataPoints/list)
- [Reconcile](https://developers.google.com/health/reference/rest/v4/users.dataTypes.dataPoints/reconcile)
- [Physical rollup](https://developers.google.com/health/reference/rest/v4/users.dataTypes.dataPoints/rollUp)
- [Daily rollup](https://developers.google.com/health/reference/rest/v4/users.dataTypes.dataPoints/dailyRollUp)
- [Webhooks](https://developers.google.com/health/webhooks)

## Compact storage

Four Google Health tables:

| Table | Purpose |
| --- | --- |
| `gh_connections` | Encrypted OAuth credentials and provider user binding |
| `gh_sync_job` | Schedule, cursor, lease, and status per connection/type/fetch method |
| `gh_records` | All points and rollups for all 39 types |
| `gh_webhook_events` | Durable verified webhook inbox |

`gh_records.raw_payload` stores the complete individual object returned inside
`dataPoints[]` or `rollupDataPoints[]`. It does not store the surrounding page
wrapper. The wrapper contains only the item array and pagination token; the
temporary token lives in `gh_sync_job.next_page_token`.

`gh_webhook_events.raw_payload` stores the complete webhook request body.
OAuth token responses are deliberately not stored raw.

OAuth state lives in Redis as
`lifestats:google-health:oauth-state:{sha256(state)}` with a 10-minute TTL.
Callback validation atomically consumes it with `GETDEL`.

## Flexible polling

Run one lightweight dispatcher every five minutes. It selects due rows:

```sql
WHERE enabled
  AND next_poll_at <= now()
  AND (lease_until IS NULL OR lease_until < now())
ORDER BY priority, next_poll_at
```

The dispatcher claims rows with `FOR UPDATE SKIP LOCKED`, sets a short
`lease_until`, then queues workers. Workers update only their selected
`(connection_id, data_type, fetch_method)` row.

Hard API capabilities remain in code. Mutable schedule lives in
`gh_sync_job`:

- `enabled`
- `poll_interval_minutes`
- `initial_lookback_days`
- `incremental_overlap_minutes`
- `page_size`
- `priority`
- `next_poll_at`

Use application timezone for quiet hours:

```text
polling window: 06:00 inclusive through 00:00 exclusive
quiet window:   00:00 inclusive through 06:00 exclusive
```

When an interval lands inside quiet hours, move `next_poll_at` to 06:00 plus
random jitter of 0–10 minutes. Manual sync bypasses quiet hours. On restart,
overdue rows run at the next permitted window.

Webhook-triggered fetches also bypass quiet hours. They are event-driven, not
polling. All 39 data types are enabled by default when their granted scope and
supported fetch method are available.

Recommended defaults:

| Tier | Interval | Initial history | Incremental overlap | Data types |
| --- | --- | --- | --- | --- |
| Activity/vitals | 15 minutes | 90 days | 2 hours | Steps, heart rate, active minutes, active-zone minutes, distance, active energy |
| Recent events | 30 minutes | 90 days | 7 days | Exercise, sleep, nutrition, hydration |
| Measurements | 60 minutes | 90 days | 7 days | Weight, body fat, glucose, oxygen, HRV, temperature, respiratory rate |
| Daily derived | 1/day at 06:10–06:30 | 90 days | 14 days | All `daily-*` types; retry once around noon |
| Rare/catalog | 6 hours or manual | 90 days | 30 days | ECG, irregular rhythm, food, food units, height |

Sleep can use a temporary 15-minute interval from 06:00–10:00, then 60
minutes. Polling faster than 15 minutes usually adds little value because
upstream wearable data commonly becomes available on roughly that cadence.

After webhooks are implemented, notification-supported types should use
webhook-triggered sync plus one daily reconciliation sweep. Polling remains the
fallback for unsupported types and missed notifications.

## Product decisions

- Manual sync bypasses quiet hours.
- Webhook-triggered sync bypasses quiet hours.
- All 39 data types poll by default.
- LifeStats does not duplicate the OAuth scope list in its own UI. Google's
  required consent screen still shows permissions; it cannot be hidden.
- Freshness timestamps are stored in `gh_records.last_synced_at` and
  `gh_sync_job.last_succeeded_at`, but are not displayed.
- `users.timezone` stores an IANA name such as `Asia/Phnom_Penh`.

## Time storage

Store every physical instant in PostgreSQL `timestamptz` and write/read it as
UTC. PostgreSQL stores an instant; session timezone only changes rendering.

Google Health supplies physical UTC timestamps plus the UTC offset and civil
time active when the event happened. Preserve the complete provider values in
`raw_payload`. Use:

- `started_at`, `ended_at`, provider timestamps: UTC `timestamptz`.
- `record_date`: provider civil date for daily records.
- `users.timezone`: frontend conversion for event timestamps.
- Provider civil date/offset: authoritative historical context during travel or
  daylight-saving changes.

Do not derive a daily record's date by converting midnight UTC. Use Google's
civil date directly.

## Recommended data policies

### Raw payload retention

For compact V2, retain `gh_records.raw_payload` as long as the record exists.
It contains fields not normalized into relational columns and enables parser
rebuilds. PostgreSQL TOAST compresses large JSONB automatically.

If typed subtype tables are added later, retain successful raw payloads for 90
days, retain normalization failures until repaired, then allow older payloads
to be re-fetched from Google.

### Reconciled versus raw-source data

Use `reconcile` by default for product reads. It combines overlapping sources
into Google's logical stream and avoids double counting.

Use `list` only when:

- The data type does not support reconcile, such as ECG, irregular rhythm,
  food, or food measurement units.
- Source-level diagnostics are explicitly needed.

Do not sync both list and reconcile for the same type by default.

### Soft deletion

Mark `deleted_at` only after a complete, successful reconcile window or a
verified webhook delete followed by confirmation. Never infer deletion from a
failed or partially paginated response.

Retain soft-deleted projection rows for 30 days. Restore them if Google returns
them again. Hard-purge after the retention window because Google remains the
source of truth.

### Retry

- Refresh once on `401`, then mark connection authorization expired.
- Honor `Retry-After` on `429`.
- Retry network errors, `408`, `429`, and `5xx`.
- Do not retry ordinary `4xx` validation/permission errors.
- Use full-jitter exponential backoff: base 1 second, cap 60 seconds, maximum 5
  attempts in one worker.
- After worker exhaustion, schedule type-level retries at approximately 5
  minutes, 15 minutes, 1 hour, then 6 hours.
- Preserve page cursor and use idempotent upserts.

### Disconnect

Disconnect should revoke/delete encrypted credentials and disable every
`gh_sync_job` row. Retain cached health projections by default, visibly mark
the connection disconnected, and offer a separate destructive “Delete cached
Google Health data” action.

Do not silently purge health history on ordinary disconnect.

### ECG and heart-rate storage

Heart rate is high-volume. Keep common timestamp/value columns indexed and
retain raw JSONB. Add monthly partitioning only after measured table/index size
justifies it; a private single-user installation may not need partitions.

ECG is rare but waveform-heavy. Keep metadata in PostgreSQL. Initially rely on
TOAST-compressed JSONB. If individual payloads or backups become excessive,
move waveform bytes to encrypted object storage and keep checksum, size, and
object key in PostgreSQL.

Never create one row per ECG waveform sample.

### Webhook timing

Implement webhooks after polling supports all enabled types and reconciliation
is proven idempotent. Then:

1. Add public HTTPS receiver and verification handshake.
2. Validate authorization and Google signature.
3. Persist event and return `204` immediately.
4. Queue affected type/range.
5. Keep daily polling reconciliation as recovery.

## Direct answer: how much data comes from one endpoint?

One read request addresses exactly one data type through `{dataType}`.

```text
users/me/dataTypes/{dataType}/dataPoints
```

The response can contain many points, but every point belongs to that selected type.
Google has no read endpoint that returns all 39 types together.

| Endpoint | Types per request | Items per response |
| --- | ---: | ---: |
| `list` | 1 | Default maximum 1,440; configurable maximum 10,000 |
| `reconcile` | 1 | Default maximum 1,440; configurable maximum 10,000 |
| `list`/`reconcile` for sleep or exercise | 1 | Maximum 25 |
| `get` | 1 | Exactly 1 identifiable point |
| `rollUp` | 1 | One item per physical-time window |
| `dailyRollUp` | 1 | One item per civil-time window |
| Exercise TCX export | 1 | One exercise file |
| Webhook | Many changed type IDs possible | Notification only; fetch records afterward |

Therefore, a full 39-type snapshot needs at least 39 read requests. Real count is:

```text
sum(pages for each data type) + optional rollup requests + retries
```

Sleep and exercise often need many pages because their page maximum is 25. For
`heart-rate`, `active-minutes`, `total-calories`, and
`calories-in-heart-rate-zone`, rollup query ranges are limited to 14 days.
Other data-type ranges are limited to 90 days.

## Read endpoint families

### 1. Reconcile: preferred application view

```http
GET /v4/users/me/dataTypes/{dataType}/dataPoints:reconcile
    ?filter={time filter}
    &pageSize={size}
    &pageToken={token}
```

Use when supported. It merges overlapping source data into one reconciled stream.
Store it with `is_reconciled = true`.

Simplified steps response:

```json
{
  "dataPoints": [
    {
      "dataPointName": "",
      "steps": {
        "interval": {
          "startTime": "2026-07-23T08:00:00Z",
          "endTime": "2026-07-23T08:01:00Z"
        },
        "count": "125"
      }
    }
  ],
  "nextPageToken": "next-page"
}
```

Continue until `nextPageToken` is absent or empty.

### 2. List: raw source points

```http
GET /v4/users/me/dataTypes/{dataType}/dataPoints
    ?filter={time filter}
    &pageSize={size}
    &pageToken={token}
```

Use for raw-source audit or types without reconciliation. Unlike reconcile,
each point can include `dataSource`.

Simplified weight response:

```json
{
  "dataPoints": [
    {
      "name": "users/health-user/dataTypes/weight/dataPoints/weight-001",
      "dataSource": {
        "recordingMethod": "MANUAL",
        "platform": "FITBIT"
      },
      "weight": {
        "sampleTime": {
          "physicalTime": "2026-07-23T06:30:00Z"
        },
        "weightGrams": 72400
      }
    }
  ],
  "nextPageToken": ""
}
```

### 3. Get: one identifiable point

```http
GET /v4/users/me/dataTypes/{dataType}/dataPoints/{dataPoint}
```

Returns one `DataPoint`, not an array. Only identifiable types support it.

Simplified response:

```json
{
  "name": "users/health-user/dataTypes/exercise/dataPoints/run-001",
  "exercise": {
    "exerciseType": "RUNNING",
    "displayName": "Morning Run",
    "activeDuration": "1800s"
  }
}
```

### 4. Daily rollup: civil-day summaries

```http
POST /v4/users/me/dataTypes/{dataType}/dataPoints:dailyRollUp
```

Simplified request:

```json
{
  "range": {
    "start": {"date": {"year": 2026, "month": 7, "day": 23}},
    "end": {"date": {"year": 2026, "month": 7, "day": 24}}
  },
  "windowSizeDays": 1,
  "pageSize": 1000,
  "dataSourceFamily": "users/me/dataSourceFamilies/all-sources"
}
```

Simplified response:

```json
{
  "rollupDataPoints": [
    {
      "civilStartTime": {
        "date": {"year": 2026, "month": 7, "day": 23}
      },
      "civilEndTime": {
        "date": {"year": 2026, "month": 7, "day": 24}
      },
      "steps": {"countSum": "3822"}
    }
  ]
}
```

Store each window in `gh_records` with `record_type = rollup` and
`fetch_method = daily_rollup`.

### 5. Physical rollup: arbitrary timestamp windows

```http
POST /v4/users/me/dataTypes/{dataType}/dataPoints:rollUp
```

Use for hourly charts or timezone-independent aggregation.

Simplified response:

```json
{
  "rollupDataPoints": [
    {
      "startTime": "2026-07-23T08:00:00Z",
      "endTime": "2026-07-23T09:00:00Z",
      "heartRate": {
        "beatsPerMinuteMin": 68,
        "beatsPerMinuteMax": 151,
        "beatsPerMinuteAvg": 104.5
      }
    }
  ]
}
```

Store each window in `gh_records` with `record_type = rollup` and
`fetch_method = rollup`.

### 6. Exercise TCX export

```http
GET /v4/users/me/dataTypes/exercise/dataPoints/{dataPoint}:exportExerciseTcx
```

Returns one exercise route/telemetry export. Treat as optional large artifact.
Do not place full TCX content in `gh_records`; use object storage plus an
artifact reference if this feature is added.

### 7. Webhook notifications

Webhook payloads indicate changed user/data types. They do not replace reads.

Processing:

1. Verify Google signature.
2. Insert raw event into `gh_webhook_events`.
3. Return success quickly.
4. Queue one sync item for each changed data type.
5. Fetch changed range through `reconcile` or `list`.

## Preferred fetch method for all 39 types

| Data type ID | Payload field | Preferred fetch | Optional aggregate |
| --- | --- | --- | --- |
| `active-energy-burned` | `activeEnergyBurned` | `reconcile` | `rollUp`, `dailyRollUp` |
| `active-minutes` | `activeMinutes` | `reconcile` | `rollUp`, `dailyRollUp` |
| `active-zone-minutes` | `activeZoneMinutes` | `reconcile` | `rollUp`, `dailyRollUp` |
| `activity-level` | `activityLevel` | `reconcile` | — |
| `altitude` | `altitude` | `reconcile` | `rollUp`, `dailyRollUp` |
| `blood-glucose` | `bloodGlucose` | `reconcile` | `rollUp`, `dailyRollUp` |
| `body-fat` | `bodyFat` | `reconcile` | `rollUp`, `dailyRollUp` |
| `calories-in-heart-rate-zone` | `caloriesInHeartRateZone` | `dailyRollUp` | `rollUp` |
| `core-body-temperature` | `coreBodyTemperature` | `reconcile` | `rollUp`, `dailyRollUp` |
| `daily-heart-rate-variability` | `dailyHeartRateVariability` | `reconcile` | — |
| `daily-heart-rate-zones` | `dailyHeartRateZones` | `reconcile` | — |
| `daily-oxygen-saturation` | `dailyOxygenSaturation` | `reconcile` | — |
| `daily-respiratory-rate` | `dailyRespiratoryRate` | `reconcile` | — |
| `daily-resting-heart-rate` | `dailyRestingHeartRate` | `reconcile` | — |
| `daily-sleep-temperature-derivations` | `dailySleepTemperatureDerivations` | `reconcile` | — |
| `daily-vo2-max` | `dailyVo2Max` | `reconcile` | — |
| `distance` | `distance` | `reconcile` | `rollUp`, `dailyRollUp` |
| `electrocardiogram` | `electrocardiogram` | `list` | — |
| `exercise` | `exercise` | `reconcile` | TCX export per point |
| `floors` | `floors` | `reconcile` | `rollUp`, `dailyRollUp` |
| `food` | `food` | `list` | — |
| `food-measurement-unit` | `foodMeasurementUnit` | `list` | — |
| `heart-rate` | `heartRate` | `reconcile` | `rollUp`, `dailyRollUp` |
| `heart-rate-variability` | `heartRateVariability` | `reconcile` | — |
| `height` | `height` | `reconcile` | `rollUp`, `dailyRollUp` |
| `hydration-log` | `hydrationLog` | `reconcile` | `rollUp`, `dailyRollUp` |
| `irregular-rhythm-notification` | `irregularRhythmNotification` | `list` | — |
| `nutrition-log` | `nutritionLog` | `reconcile` | `rollUp`, `dailyRollUp` |
| `oxygen-saturation` | `oxygenSaturation` | `reconcile` | — |
| `respiratory-rate-sleep-summary` | `respiratoryRateSleepSummary` | `reconcile` | — |
| `run-vo2-max` | `runVo2Max` | `reconcile` | `rollUp`, `dailyRollUp` |
| `sedentary-period` | `sedentaryPeriod` | `reconcile` | `rollUp`, `dailyRollUp` |
| `sleep` | `sleep` | `reconcile` | — |
| `steps` | `steps` | `reconcile` | `rollUp`, `dailyRollUp` |
| `swim-lengths-data` | `swimLengthsData` | `reconcile` | `rollUp`, `dailyRollUp` |
| `time-in-heart-rate-zone` | `timeInHeartRateZone` | `reconcile` | `rollUp`, `dailyRollUp` |
| `total-calories` | `totalCalories` | `dailyRollUp` | `rollUp` |
| `vo2-max` | `vo2Max` | `reconcile` | — |
| `weight` | `weight` | `reconcile` | `rollUp`, `dailyRollUp` |

Do not assume unsupported operations. Keep exact capabilities in a
version-controlled code registry next to fetch and parsing logic.

## Database write algorithm

For each `gh_sync_job` row:

1. Read endpoint strategy and limits from the code registry.
2. Split requested date range into 14-day or 90-day windows.
3. Fetch pages until token exhaustion.
4. Extract common envelope fields: date, start, end, provider name, source.
5. Preserve each complete returned item in `gh_records.raw_payload`.
6. Compute stable `identity_hash`; upsert without duplicating retries.
7. Compute `payload_hash`; skip unchanged updates.
8. Mark records missing from a fully reconciled window as deleted.
9. Save temporary pagination progress in `gh_sync_job`.
10. Advance `last_succeeded_at` only after complete window success.

Never flatten all union payloads into one giant nullable table. Keep raw JSONB,
then add typed projection tables or materialized views only for product queries.
