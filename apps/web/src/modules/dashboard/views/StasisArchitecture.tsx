import type { Dashboard } from "@/lib/types";

export function StasisArchitecture({
  data,
  date,
  onDateChange,
}: {
  data: Dashboard;
  date: string;
  onDateChange: (date: string) => void;
}) {
  const sleep = data.metrics.find((metric) => metric.key === "sleep");
  const sessions = data.timeline.filter((item) => item.kind === "sleep");

  return (
    <div className="viewStack">
      <header className="pageHeader sleepHeader">
        <div>
          <p className="eyebrow">Google Health sleep</p>
          <h1>Stasis Architecture</h1>
          <p>Sleep duration and session availability from the selected day.</p>
        </div>
        <label className="dateControl">
          <span>Date</span>
          <input
            aria-label="Sleep date"
            onChange={(event) => onDateChange(event.target.value)}
            type="date"
            value={date}
          />
        </label>
      </header>

      <section className="sleepHero" aria-labelledby="sleep-summary-title">
        <div className="sleepDial" aria-label={sleep?.value != null ? `${sleep.value} hours asleep` : "Sleep duration unavailable"}>
          <div>
            <strong>{sleep?.value ?? "—"}</strong>
            <span>{sleep?.value != null ? "hours" : "not synced"}</span>
          </div>
        </div>
        <div className="sleepSummary">
          <p className="sectionKicker">Selected night</p>
          <h2 id="sleep-summary-title">Sleep duration</h2>
          <p>
            {sleep?.value != null
              ? `Google Health reported ${sleep.value} hours of sleep for ${sleep.observedAt}.`
              : "No sleep session has been synced for this date."}
          </p>
          <dl className="inlineFacts">
            <div>
              <dt>Source</dt>
              <dd>{sleep?.source ?? "Google Health"}</dd>
            </div>
            <div>
              <dt>Freshness</dt>
              <dd>{sleep?.freshness ?? "unknown"}</dd>
            </div>
            <div>
              <dt>Availability</dt>
              <dd>{sleep?.availability.replaceAll("-", " ") ?? "not synced"}</dd>
            </div>
          </dl>
        </div>
      </section>

      <section className="panel" aria-labelledby="architecture-title">
        <div className="panelHeading">
          <div>
            <p className="sectionKicker">Sleep composition</p>
            <h2 id="architecture-title">Architecture details</h2>
          </div>
          <span className="unsupportedPill">Current API gap</span>
        </div>
        <div className="architectureGrid">
          {[
            ["Time in bed", "Not available"],
            ["Sleep stages", "Not available"],
            ["Sleep efficiency", "Not available"],
            ["Respiratory rate", "Not available"],
          ].map(([label, value]) => (
            <div className="architectureCell" key={label}>
              <span>{label}</span>
              <strong>{value}</strong>
              <small>Not exposed by current dashboard contract</small>
            </div>
          ))}
        </div>
        <p className="sourceNote">
          LifeStats does not estimate missing sleep stages or present a local sleep score.
        </p>
      </section>

      <section className="panel" aria-labelledby="sessions-title">
        <div className="panelHeading">
          <div>
            <p className="sectionKicker">Synced records</p>
            <h2 id="sessions-title">Sleep sessions</h2>
          </div>
          <span className="countPill">{sessions.length} sessions</span>
        </div>
        {sessions.length ? (
          <ol className="sessionList">
            {sessions.map((session) => (
              <li key={session.id}>
                <span className="sessionMoon" aria-hidden="true">☾</span>
                <div>
                  <strong>{session.title}</strong>
                  <p>{session.detail ?? "Sleep session"}</p>
                </div>
                <div>
                  <time dateTime={session.occurredAt}>
                    {new Date(session.occurredAt).toLocaleString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                      month: "short",
                      day: "numeric",
                    })}
                  </time>
                  <span>{session.source}</span>
                </div>
              </li>
            ))}
          </ol>
        ) : (
          <div className="emptyState compactEmpty">
            <span aria-hidden="true">☾</span>
            <strong>No sleep session synced</strong>
            <p>Try syncing Google Health or selecting another date.</p>
          </div>
        )}
      </section>
    </div>
  );
}
