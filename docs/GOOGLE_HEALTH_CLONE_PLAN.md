# Google Health base-feature clone plan

Research date: 2026-07-22.

## Target definition

This project targets the redesigned Google Health app that replaced the Fitbit app beginning May 19, 2026. It does not target Google Fit or the Android Health Connect settings application.

For a connected Fitbit device or Pixel Watch, the official application uses four primary tabs:

1. Today
2. Fitness
3. Sleep
4. Health

Users without a connected device receive only Today and Health. LifeStats will initially target the connected-device experience because its Google Health API account already exposes Fitbit and Pixel Watch data.

## Official research

- [Google Health redesign](https://support.google.com/googlehealth/answer/17068213): product rename, four-tab organization, Premium separation, and removed legacy features.
- [Official feature map](https://support.google.com/product-documentation/answer/17081467): Today, Fitness, Sleep, and Health feature inventory.
- [Explore Google Health](https://support.google.com/googlehealth/answer/14237011): customizable Today metrics and Fitness examples.
- [Google Health API](https://developers.google.com/health): API purpose and relationship to the former Fitbit Web API.
- [Google Health API data types](https://developers.google.com/health/data-types): current records, operations, scopes, and naming rules.
- [Workout experiences](https://developers.google.com/health/data-types/workouts): exercise sessions, summary metrics, telemetry, and write behavior.
- [Readiness](https://support.google.com/googlehealth/answer/14236710): official score behavior; algorithm is not exposed as a Google Health API data type.
- [Sleep](https://support.google.com/googlehealth/answer/14236407) and [Sleep Score](https://support.google.com/googlehealth/answer/14236513): sleep information architecture and official score behavior.
- [Nutrition and hydration](https://support.google.com/googlehealth/answer/14237210): base logging and review workflows.

## Product principles

- Google Health API owns health truth.
- Local rows are synchronized projections.
- Every displayed metric carries freshness and availability state.
- Official scores appear only when an official API field supports them.
- Missing API support produces an explicit unavailable state, never a substitute score.
- Use original LifeStats visuals. Clone product capabilities and hierarchy, not protected branding or assets.

## Phase 0: clean baseline

Remove current features outside the base product:

- AI Coach and OpenAI response plumbing.
- Local journals and correlation insights.
- Local strength-session and set logger.
- Custom recovery, strain, stress, energy, and sleep scores.
- Standalone generic Trends and Data Explorer product navigation.

Preserve their historical database tables and baseline migration. Database deletion requires a separate retention decision.

Retain only source-backed foundations:

- Google OAuth and account binding.
- Google Health synchronization.
- Today shell.
- Activity and workout history.
- Sleep sessions and supported sleep detail.
- Vitals and health measurements.
- Nutrition writes and synchronized nutrition reads.
- Sync status and diagnostics.

## Phase 1: application shell

Create four responsive destinations:

| Tab | Route | Initial responsibility |
| --- | --- | --- |
| Today | `/dashboard` | Focus metrics, recent exercise/sleep, quick logging, sync freshness |
| Fitness | `/fitness` | Steps, distance, energy, zone minutes, VO2 max, exercises |
| Sleep | `/sleep` | Duration, stages, schedule, efficiency inputs, quality metrics |
| Health | `/health` | Vitals, heart, metabolic measurements, nutrition, hydration |

Shared requirements:

- Date/range selector.
- Loading, empty, stale, permission-denied, and sync-error states.
- Units and timezone normalization.
- Source and last-updated disclosure.
- Accessible keyboard and screen-reader behavior.

## Phase 2: Today

Base cards:

- Steps.
- Active Zone Minutes or active minutes.
- Weekly cardio-load availability state.
- Latest sleep duration.
- Resting heart rate.
- Readiness availability state.
- Recent exercise and sleep sessions.
- Nutrition/hydration quick actions where supported.

Today metrics become user-configurable after the static base is stable.

## Phase 3: Fitness

Implement from current API-supported data:

- Steps and hourly/daily trends.
- Distance.
- Active and total energy.
- Active minutes and Active Zone Minutes.
- Floors and altitude where available.
- Daily/run VO2 max.
- Exercise history and detail.
- Exercise summary: duration, distance, steps, calories, average heart rate.
- Detailed heart-rate and route overlays only when telemetry/location permissions exist.

Do not implement Premium plans, workout video library cloning, or coaching in the base milestone.

## Phase 4: Sleep

Implement:

- Primary sleep session.
- Start/end schedule.
- Duration and time awake.
- Sleep stages.
- Respiratory-rate sleep summary.
- Overnight oxygen, HRV, resting heart rate, and temperature context where available.
- Week/month/year trends.

The official Sleep Score algorithm is not exposed in the current API data-type catalog. Show official score only if a future source field becomes available.

## Phase 5: Health

Initial groups:

- Vitals: HRV, breathing rate, temperature, resting heart rate, SpO2.
- Heart: heart rate, zones, ECG, irregular-rhythm notifications when scope/device permits.
- Metabolic: weight, body fat, glucose, height.
- Fitness health: VO2 max.
- Nutrition: food catalog, nutrition logs, calories, macros.
- Hydration: water logs and totals.

Cycle health, mindfulness, basal measurements, and blood pressure are deferred. Google lists several of these for later API availability rather than the current catalog.

## Phase 6: synchronization correctness

- Use reconciled-stream pagination and bounded replacement windows; Google Health does not expose a persistent change cursor for these reads.
- Add webhook ingestion for supported data types.
- Reconcile deletions and edits from Google Health.
- Make sync idempotent.
- Record per-type permission, freshness, cursor, error, and last-success state.
- Add projection rebuild command.
- Ensure writes complete remotely before local projection refresh.

## Acceptance criteria

- Primary navigation contains only Today, Fitness, Sleep, and Health.
- No Coach, Journal, Strength, Recovery, or Strain routes remain.
- Health UI reads only synchronized Google Health projections.
- Supported writes go through Google Health and then resync.
- Unsupported official metrics are labeled unavailable.
- All health views show freshness/error state.
- Historical migrations remain nondestructive.
- Ruff, formatting, mypy, pytest, ESLint, TypeScript, Next.js build, migration compatibility, and Docker checks pass.
