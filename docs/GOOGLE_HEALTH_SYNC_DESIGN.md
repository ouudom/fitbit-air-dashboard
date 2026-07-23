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
| `gh_sync_state` | One current sync cursor/status row per connection and data type |
| `gh_records` | All points and rollups for all 39 types |
| `gh_webhook_events` | Durable verified webhook inbox |

`gh_records.raw_payload` stores the complete individual object returned inside
`dataPoints[]` or `rollupDataPoints[]`. It does not store the surrounding page
wrapper. The wrapper contains only the item array and pagination token; the
temporary token lives in `gh_sync_state.next_page_token`.

`gh_webhook_events.raw_payload` stores the complete webhook request body.
OAuth token responses are deliberately not stored raw.

OAuth state lives in Redis as
`lifestats:google-health:oauth-state:{sha256(state)}` with a 10-minute TTL.
Callback validation atomically consumes it with `GETDEL`.

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

For each `gh_sync_state` row:

1. Read endpoint strategy and limits from the code registry.
2. Split requested date range into 14-day or 90-day windows.
3. Fetch pages until token exhaustion.
4. Extract common envelope fields: date, start, end, provider name, source.
5. Preserve each complete returned item in `gh_records.raw_payload`.
6. Compute stable `identity_hash`; upsert without duplicating retries.
7. Compute `payload_hash`; skip unchanged updates.
8. Mark records missing from a fully reconciled window as deleted.
9. Save temporary pagination progress in `gh_sync_state`.
10. Advance `last_succeeded_at` only after complete window success.

Never flatten all union payloads into one giant nullable table. Keep raw JSONB,
then add typed projection tables or materialized views only for product queries.
