# LifeStats modular architecture

## Dependency rule

`presentation → application → domain`. Infrastructure implements domain/application ports. Domain never imports FastAPI, SQLAlchemy, HTTPX, Celery, Next.js, or provider payload types.

One bounded context must not import another context’s infrastructure. Cross-context orchestration belongs in an application service and depends on a semantic port. The dashboard is a read-model composer; it does not own source records.

## Data ownership

| Context | Owns |
| --- | --- |
| Identity | private admin, sessions, setup lifecycle |
| Google Health | OAuth connection, transport, sync jobs, provider writes |
| Habits | definitions, schedules, completion records |
| Scoring | versioned LifeStats score model and score projections |
| Timeline | merged event read model |
| Dashboard | Today response composition |

Legacy `daily_metrics`, `health_records`, `exercises`, `sync_state`, and `daily_scores` remain compatibility projections. Google Health can rebuild health projections. Legacy token and journal rows remain untouched for rollback.

## Future contexts

Fitness, meditation, food, biology, Alfred, Telegram, and Todoist receive modules only when implemented. No placeholder packages or navigation routes.
