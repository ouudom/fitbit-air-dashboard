import type { Dashboard } from "@/lib/types";
import { MetricCard } from "../components/MetricCard";

type BatcaveOverviewProps = {
  data: Dashboard;
  date: string;
  onDateChange: (date: string) => void;
  onOpenSleep: () => void;
  onSync: () => void;
  syncError?: string;
  syncing: boolean;
};

export function BatcaveOverview({
  data,
  date,
  onDateChange,
  onOpenSleep,
  onSync,
  syncError,
  syncing,
}: BatcaveOverviewProps) {
  const errors = data.sync.filter((item) => item.status === "error");
  const syncedRecords = data.sync.reduce((total, item) => total + item.recordCount, 0);

  return (
    <div className="viewStack">
      <header className="pageHeader">
        <div>
          <p className="eyebrow">Private health dashboard</p>
          <h1>Batcave Overview</h1>
          <p>Latest source-backed signals and Google Health sync activity.</p>
        </div>
        <div className="headerActions">
          <label className="dateControl">
            <span>Date</span>
            <input
              aria-label="Dashboard date"
              onChange={(event) => onDateChange(event.target.value)}
              type="date"
              value={date}
            />
          </label>
          <a className="secondaryButton" href="/api/v1/integrations/google-health/connect">
            Connect Google Health
          </a>
          <button className="primaryButton" disabled={syncing} onClick={onSync}>
            <span className={syncing ? "syncGlyph spinning" : "syncGlyph"} aria-hidden="true">
              ↻
            </span>
            {syncing ? "Syncing…" : "Sync data"}
          </button>
        </div>
      </header>

      {syncError && <p className="errorBanner" role="alert">{syncError}</p>}

      <section aria-labelledby="signals-title">
        <div className="sectionHeading">
          <div>
            <p className="sectionKicker">Daily data</p>
            <h2 id="signals-title">Primary signals</h2>
          </div>
          <span>{data.timezone}</span>
        </div>
        <div className="metricGrid">
          {data.metrics.map((metric) => (
            <MetricCard
              key={metric.key}
              metric={metric}
              onOpen={metric.key === "sleep" ? onOpenSleep : undefined}
            />
          ))}
        </div>
      </section>

      <div className="overviewGrid">
        <section className="panel timelinePanel" aria-labelledby="timeline-title">
          <div className="panelHeading">
            <div>
              <p className="sectionKicker">Selected day</p>
              <h2 id="timeline-title">Health timeline</h2>
            </div>
            <span className="countPill">{data.timeline.length} events</span>
          </div>
          {data.timeline.length ? (
            <ol className="timeline">
              {data.timeline.map((item) => (
                <li key={item.id}>
                  <span className="timelineDot" aria-hidden="true" />
                  <time dateTime={item.occurredAt}>
                    {new Date(item.occurredAt).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </time>
                  <div>
                    <strong>{item.title}</strong>
                    <p>{item.detail ?? item.kind}</p>
                  </div>
                  <span className="sourceLabel">{item.source}</span>
                </li>
              ))}
            </ol>
          ) : (
            <div className="emptyState">
              <span aria-hidden="true">○</span>
              <strong>No events for this day</strong>
              <p>Sync Google Health or select another date.</p>
            </div>
          )}
        </section>

        <aside className="panel sourcePanel" aria-labelledby="source-title">
          <div className="panelHeading">
            <div>
              <p className="sectionKicker">Data provenance</p>
              <h2 id="source-title">Source status</h2>
            </div>
          </div>
          <dl className="statusList">
            <div>
              <dt>Connected streams</dt>
              <dd>{data.sync.length}</dd>
            </div>
            <div>
              <dt>Projected records</dt>
              <dd>{syncedRecords.toLocaleString()}</dd>
            </div>
            <div>
              <dt>Streams needing attention</dt>
              <dd>{errors.length}</dd>
            </div>
          </dl>
          <p className="sourceNote">
            Google Health remains source of truth. Local rows are rebuildable projections.
          </p>
        </aside>
      </div>
    </div>
  );
}
