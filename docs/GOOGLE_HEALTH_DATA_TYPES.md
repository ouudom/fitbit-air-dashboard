# Google Health data types

Current as of 2026-07-23. Source: [Google Health API data types](https://developers.google.com/health/data-types).

Examples are illustrative values, not complete API payloads. Endpoint identifiers use kebab case.

## Current LifeStats coverage

| Data type | ID | V2 storage | Example |
| --- | --- | --- | --- |
| Active Minutes | `active-minutes` | `gh_records` | `42 min` on `2026-07-23` |
| Daily Heart Rate Variability | `daily-heart-rate-variability` | `gh_records` | `47.5 ms` daily average |
| Daily Resting Heart Rate | `daily-resting-heart-rate` | `gh_records` | `58 bpm` |
| Exercise | `exercise` | `gh_records` | Running, `35 min`, `5 km`, `380 kcal` |
| Heart Rate | `heart-rate` | `gh_records` | `142 bpm` at `08:14:30Z` |
| Hydration Log | `hydration-log` | `gh_records` | `500 ml` water |
| Nutrition Log | `nutrition-log` | `gh_records` | Oatmeal, `320 kcal`, `12 g` protein |
| Sleep | `sleep` | `gh_records` | `23:05–06:45`, `7 h 12 min` asleep |
| Steps | `steps` | `gh_records` | `3,822 steps` |
| Weight | `weight` | `gh_records` | `72.4 kg` |

## Complete Google Health API catalog

| Category | Data type | Endpoint ID | Record kind | Illustrative example |
| --- | --- | --- | --- | --- |
| Activity | Active Energy Burned | `active-energy-burned` | Interval | `523.4 kcal` |
| Activity | Active Minutes | `active-minutes` | Interval | `42 min` |
| Activity | Active Zone Minutes | `active-zone-minutes` | Interval | `28 zone min` |
| Activity | Activity Level | `activity-level` | Interval | `ACTIVE` from `08:00–08:30` |
| Activity | Altitude | `altitude` | Interval | `34.2 m` |
| Health | Blood Glucose | `blood-glucose` | Sample | `97 mg/dL` |
| Health | Body Fat | `body-fat` | Sample | `18.6%` |
| Activity | Calories In Heart Rate Zone | `calories-in-heart-rate-zone` | Rollup | Cardio zone: `75 kcal` |
| Health | Core Body Temperature | `core-body-temperature` | Sample | `37.0 °C` |
| Health | Daily Heart Rate Variability | `daily-heart-rate-variability` | Daily | `47.5 ms` |
| Health | Daily Heart Rate Zones | `daily-heart-rate-zones` | Daily | Cardio zone: `22 min` |
| Health | Daily Oxygen Saturation | `daily-oxygen-saturation` | Daily | Average `97%` |
| Health | Daily Respiratory Rate | `daily-respiratory-rate` | Daily | `14.2 breaths/min` |
| Health | Daily Resting Heart Rate | `daily-resting-heart-rate` | Daily | `58 bpm` |
| Health | Daily Sleep Temperature Derivations | `daily-sleep-temperature-derivations` | Daily | Baseline deviation `+0.2 °C` |
| Activity | Daily VO2 Max | `daily-vo2-max` | Daily | `44 ml/kg/min` |
| Activity | Distance | `distance` | Interval | `5,000 m` |
| ECG | Electrocardiogram | `electrocardiogram` | Session | `30 s` ECG, sinus rhythm |
| Activity | Exercise | `exercise` | Session | Morning run, `35 min`, `5 km` |
| Activity | Floors | `floors` | Interval | `12 floors` |
| Nutrition | Food | `food` | Food | Banana, `105 kcal` per serving |
| Nutrition | Food Measurement Unit | `food-measurement-unit` | Food | Gram, `g` |
| Health | Heart Rate | `heart-rate` | Sample | `142 bpm` |
| Health | Heart Rate Variability | `heart-rate-variability` | Sample | `51 ms` |
| Health | Height | `height` | Sample | `1.75 m` |
| Nutrition | Hydration Log | `hydration-log` | Session | `500 ml` water |
| Heart | Irregular Rhythm Notification | `irregular-rhythm-notification` | Session | Possible atrial fibrillation notification |
| Nutrition | Nutrition Log | `nutrition-log` | Sample | Oatmeal, calories and macros |
| Health | Oxygen Saturation | `oxygen-saturation` | Sample | `98%` |
| Health | Respiratory Rate Sleep Summary | `respiratory-rate-sleep-summary` | Sample | Sleep average `13.8 breaths/min` |
| Activity | Run VO2 Max | `run-vo2-max` | Sample | `46 ml/kg/min` |
| Activity | Sedentary Period | `sedentary-period` | Interval | Seated for `60 min` |
| Sleep | Sleep | `sleep` | Session | Sleep interval with awake/light/deep/REM stages |
| Activity | Steps | `steps` | Interval | `3,822 steps` |
| Activity | Swim Lengths Data | `swim-lengths-data` | Interval | `40` pool lengths |
| Activity | Time in Heart Rate Zone | `time-in-heart-rate-zone` | Interval | Cardio zone: `1,200 s` |
| Activity | Total Calories | `total-calories` | Rollup | `2,200 kcal` |
| Activity | VO2 Max | `vo2-max` | Sample | `45 ml/kg/min` |
| Health | Weight | `weight` | Sample | `72.4 kg` |

## Storage rule

- `gh_records`: all provider points and rollups, with complete item JSON in
  `raw_payload`.
- Common query fields stay relational: type, date, start, end, provider name.
- Add typed views or projections later only when real product queries require them.
- Enable each of the 39 types only after its fetch and identity-hash contract is tested.
