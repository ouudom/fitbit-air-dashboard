# LifeStats modular architecture

## Backend layout

`apps/api/src` contains global app wiring, `core`, and domain `modules`.

- `router.py`: FastAPI transport only.
- `dependencies.py`: optional module-owned FastAPI dependencies.
- `schemas.py`: Pydantic request and response contracts.
- `service.py`: module orchestration and business rules.
- `models.py`: module-owned SQLAlchemy mappings.
- `domain.py`: optional pure domain types and calculations.

Complex integrations may add focused adapter files. Google Health owns its OAuth, client, synchronization, encryption, remote writes, and Celery tasks. Cross-module composition imports public services or domain contracts. The dashboard remains a read-model composer; it owns no source records.

## Data ownership

| Context | Owns |
| --- | --- |
| Identity | private admin, sessions, setup lifecycle |
| Google Health | OAuth connection, transport, sync jobs, provider writes |
| Scoring | versioned LifeStats score model and score projections |
| Timeline | merged event read model |
| Dashboard | Today response composition |

Legacy `daily_metrics`, `health_records`, `exercises`, `sync_state`, and `daily_scores` remain compatibility projections. Google Health can rebuild health projections. Legacy token, journal, and habit rows remain untouched for rollback.

## Future contexts

Fitness, meditation, food, biology, Alfred, Telegram, and Todoist receive modules only when implemented. No placeholder packages or navigation routes.
