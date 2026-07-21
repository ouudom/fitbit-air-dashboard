# LifeStats wellness scoring specification

Model: `wellness-v1.0.0`

Scores are experimental wellness estimates. Not medical devices, diagnoses, or treatment guidance. Every score records model version, available inputs, personal baseline, contribution direction, confidence, and calculation state.

## Baselines and gating

- Baselines use prior 60 days and robust median/MAD normalization.
- Scores remain `calibrating` until 21 historical observations exist.
- High confidence requires all inputs and at least 28 baseline days.
- Missing inputs reduce confidence. They never become zero or normal values.
- Values clamp to 0–100. Recalculation remains deterministic after late Fitbit syncs.

## Scores

- Recovery: HRV and resting heart rate receive 1.5× weight; respiratory rate, SpO₂, and temperature deviation receive 1×.
- Sleep: equal-weight duration sufficiency against eight hours, efficiency, and continuity. Stages remain descriptive.
- Strain: steps, Active Zone Minutes, and active energy normalized against personal history. Zone minutes carry largest contribution.
- Physiological Stress: inverse HRV plus elevated resting heart rate, with movement context. Not mental-stress measurement.
- Energy: equal-weight Recovery, Sleep, inverse Strain, and inverse physiological Stress.

## Evidence rules

Journal correlation stays unavailable until a habit has at least five exposed and five unexposed days. UI must display sample counts and “correlation is not causation.” Formula changes require new model version and snapshot tests.
