import { Card, Chip, Surface, Typography } from "@heroui/react";
import { AppTextField } from "@/components/ui/AppTextField";
import { EmptyContent } from "@/components/ui/EmptyContent";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionHeader } from "@/components/ui/SectionHeader";
import type { Dashboard } from "@/lib/types";

type SleepDetail = NonNullable<Dashboard["sleep"]>;
type StageSegment = SleepDetail["stages"][number];

const STAGE_META: Record<string, { label: string; color: string }> = {
  AWAKE: { label: "Awake", color: "var(--sleep-awake)" },
  RESTLESS: { label: "Restless", color: "var(--sleep-restless)" },
  ASLEEP: { label: "Asleep", color: "var(--sleep-light)" },
  REM: { label: "REM", color: "var(--sleep-rem)" },
  LIGHT: { label: "Light", color: "var(--sleep-light)" },
  DEEP: { label: "Deep", color: "var(--sleep-deep)" },
};

export function SleepOverview({
  data,
  date,
  onDateChange,
}: {
  data: Dashboard;
  date: string;
  onDateChange: (date: string) => void;
}) {
  const detail = data.sleep;
  const sessions = data.timeline.filter((item) => item.kind === "sleep");

  return (
    <div className="mx-auto grid w-full max-w-6xl gap-6">
      <PageHeader
        actions={
          <AppTextField
            className="w-40 max-sm:basis-full"
            inputProps={{
              "aria-label": "Sleep date",
              onChange: (event) => onDateChange(event.target.value),
              type: "date",
              value: date,
            }}
            label="Date"
          />
        }
        description="Session timing and sleep stages reported by Google Health."
        eyebrow="Google Health sleep"
        title="Sleep"
      />

      {detail ? (
        <>
          <SleepHero detail={detail} timezone={data.timezone} />
          <SleepTimeline detail={detail} timezone={data.timezone} />
          <SleepFacts detail={detail} />
        </>
      ) : (
        <Card variant="secondary">
          <Card.Content>
            <EmptyContent
              description="Try syncing Google Health or selecting another date."
              icon="☾"
              title="No sleep session synced"
            />
          </Card.Content>
        </Card>
      )}

      <Card variant="secondary" aria-labelledby="sessions-title">
        <Card.Header>
          <SectionHeader
            action={
              <Chip size="sm" variant="soft">
                <Chip.Label>{sessions.length} sessions</Chip.Label>
              </Chip>
            }
            eyebrow="Selected day"
            id="sessions-title"
            title="Sleep sessions"
          />
        </Card.Header>
        <Card.Content>
          {sessions.length ? (
            <ol className="grid">
              {sessions.map((session) => (
                <li
                  className="grid grid-cols-[36px_minmax(0,1fr)_auto] items-center gap-3 border-b border-separator py-3 last:border-0 max-sm:grid-cols-[36px_minmax(0,1fr)]"
                  key={session.id}
                >
                  <Surface
                    className="grid size-9 place-items-center rounded-full text-lg text-accent"
                    variant="tertiary"
                    aria-hidden="true"
                  >
                    ☾
                  </Surface>
                  <div className="min-w-0">
                    <Typography weight="semibold">{session.title}</Typography>
                    <Typography.Paragraph color="muted" size="xs">
                      {session.detail ?? "Sleep session"}
                    </Typography.Paragraph>
                  </div>
                  <div className="text-right max-sm:col-start-2 max-sm:text-left">
                    <time className="block text-xs tabular-nums" dateTime={session.occurredAt}>
                      {formatTime(session.occurredAt, data.timezone)}
                    </time>
                    <Typography color="muted" type="body-xs">
                      {session.source}
                    </Typography>
                  </div>
                </li>
              ))}
            </ol>
          ) : (
            <EmptyContent
              description="No additional sessions were found for this date."
              icon="☾"
              title="No session in timeline"
            />
          )}
        </Card.Content>
      </Card>
    </div>
  );
}

function SleepHero({ detail, timezone }: { detail: SleepDetail; timezone: string }) {
  return (
    <Card variant="default" aria-labelledby="sleep-duration-title">
      <Card.Content className="grid gap-8 p-7 max-sm:p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <Typography
              className="mb-2 uppercase tracking-[0.1em] text-accent"
              type="body-xs"
              weight="bold"
            >
              Selected night
            </Typography>
            <Typography.Heading id="sleep-duration-title" level={2}>
              Sleep duration
            </Typography.Heading>
          </div>
          <Chip color="success" size="sm" variant="soft">
            <Chip.Label>{detail.freshness}</Chip.Label>
          </Chip>
        </div>

        <div className="flex flex-wrap items-end gap-x-5 gap-y-2">
          <span className="text-6xl font-bold leading-none tracking-[-0.04em] tabular-nums max-sm:text-5xl">
            {formatMinutes(detail.minutesAsleep)}
          </span>
          <span className="pb-1 text-lg font-semibold tabular-nums text-muted">
            {formatTime(detail.startAt, timezone)}–{formatTime(detail.endAt, timezone)}
          </span>
        </div>

        <Typography.Paragraph className="max-w-[70ch]" color="muted" size="sm">
          Google Health recorded {formatMinutes(detail.minutesInSleepPeriod)} in the sleep
          period. Sleep efficiency was {formatPercent(detail.sleepEfficiency)}, calculated
          from synced duration fields.
        </Typography.Paragraph>

        <dl className="grid grid-cols-4 gap-3 max-lg:grid-cols-2 max-sm:grid-cols-1">
          <Metric label="In sleep period" value={formatMinutes(detail.minutesInSleepPeriod)} />
          <Metric label="Asleep" value={formatMinutes(detail.minutesAsleep)} />
          <Metric label="Awake" value={formatMinutes(detail.minutesAwake)} />
          <Metric label="Sleep efficiency" value={formatPercent(detail.sleepEfficiency)} />
        </dl>
      </Card.Content>
    </Card>
  );
}

function SleepTimeline({ detail, timezone }: { detail: SleepDetail; timezone: string }) {
  const sessionStart = new Date(detail.startAt).getTime();
  const sessionEnd = new Date(detail.endAt).getTime();
  const midpoint = new Date(sessionStart + (sessionEnd - sessionStart) / 2).toISOString();
  const stageTypes = detail.stageSummary
    .map((stage) => stage.type)
    .filter((type) => type in STAGE_META);

  return (
    <Card variant="secondary" aria-labelledby="sleep-stages-title">
      <Card.Header>
        <SectionHeader
          action={
            <Chip size="sm" variant="soft">
              <Chip.Label>{detail.stages.length} segments</Chip.Label>
            </Chip>
          }
          eyebrow="Sleep composition"
          id="sleep-stages-title"
          title="Stage timeline"
        />
      </Card.Header>
      <Card.Content className="grid gap-5">
        {stageTypes.length ? (
          <div className="grid gap-4">
            {stageTypes.map((type) => {
              const summary = detail.stageSummary.find((stage) => stage.type === type);
              const meta = STAGE_META[type];
              return (
                <div className="grid gap-2" key={type}>
                  <div className="flex items-baseline justify-between gap-3">
                    <Typography weight="semibold">{meta.label}</Typography>
                    <Typography className="tabular-nums" color="muted" type="body-sm">
                      {formatMinutes(summary?.minutes ?? null)} · {summary?.count ?? 0} periods
                    </Typography>
                  </div>
                  <StageTrack
                    color={meta.color}
                    end={sessionEnd}
                    label={`${meta.label} stage timeline`}
                    segments={detail.stages.filter((stage) => stage.type === type)}
                    start={sessionStart}
                  />
                </div>
              );
            })}
            <div className="flex justify-between text-xs tabular-nums text-muted">
              <time dateTime={detail.startAt}>{formatTime(detail.startAt, timezone)}</time>
              <time dateTime={midpoint}>{formatTime(midpoint, timezone)}</time>
              <time dateTime={detail.endAt}>{formatTime(detail.endAt, timezone)}</time>
            </div>
          </div>
        ) : (
          <EmptyContent
            description="This session has duration data but no processed sleep stages."
            title="Sleep stages unavailable"
          />
        )}
        <Typography.Paragraph color="muted" size="xs">
          Stage colors show Google Health classifications. They do not indicate good or bad
          sleep.
        </Typography.Paragraph>
      </Card.Content>
    </Card>
  );
}

function StageTrack({
  color,
  end,
  label,
  segments,
  start,
}: {
  color: string;
  end: number;
  label: string;
  segments: StageSegment[];
  start: number;
}) {
  const duration = Math.max(end - start, 1);
  return (
    <div
      aria-label={label}
      className="relative h-10 overflow-hidden rounded-2xl bg-[var(--surface-inset)] ring-1 ring-inset ring-[var(--border)]"
      role="img"
    >
      {segments.map((segment, index) => {
        const segmentStart = new Date(segment.startAt).getTime();
        const segmentEnd = new Date(segment.endAt).getTime();
        const left = Math.max(0, ((segmentStart - start) / duration) * 100);
        const width = Math.max(0.35, ((segmentEnd - segmentStart) / duration) * 100);
        return (
          <span
            className="absolute inset-y-0 rounded-md"
            key={`${segment.startAt}-${index}`}
            style={{
              backgroundColor: color,
              left: `${left}%`,
              width: `${Math.min(width, 100 - left)}%`,
            }}
          />
        );
      })}
    </div>
  );
}

function SleepFacts({ detail }: { detail: SleepDetail }) {
  const timingFacts = [
    ["Time to fall asleep", formatMinutes(detail.minutesToFallAsleep)],
    ["After final wake-up", formatMinutes(detail.minutesAfterWakeUp)],
    ["Stage data", detail.stages.length ? `${detail.stages.length} segments` : "Unavailable"],
    ["Source", detail.source],
  ];

  return (
    <Card variant="secondary" aria-labelledby="sleep-details-title">
      <Card.Header>
        <SectionHeader
          action={
            <Chip size="sm" variant="tertiary">
              <Chip.Label>Source-backed</Chip.Label>
            </Chip>
          }
          eyebrow="Night details"
          id="sleep-details-title"
          title="Sleep timing"
        />
      </Card.Header>
      <Card.Content>
        <dl className="grid grid-cols-4 gap-3 max-lg:grid-cols-2 max-sm:grid-cols-1">
          {timingFacts.map(([label, value]) => (
            <Metric key={label} label={label} value={value} />
          ))}
        </dl>
      </Card.Content>
      <Card.Footer>
        <Typography.Paragraph color="muted" size="xs">
          {detail.derivation} Last synced{" "}
          <time dateTime={detail.lastSyncedAt}>
            {new Date(detail.lastSyncedAt).toLocaleString()}
          </time>
          .
        </Typography.Paragraph>
      </Card.Footer>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <Surface className="grid gap-1.5 p-4" variant="tertiary">
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="text-lg font-semibold tabular-nums">{value}</dd>
    </Surface>
  );
}

function formatMinutes(value: number | null | undefined): string {
  if (value == null) return "Unavailable";
  const hours = Math.floor(value / 60);
  const minutes = Math.round(value % 60);
  if (!hours) return `${minutes}m`;
  return minutes ? `${hours}h ${minutes}m` : `${hours}h`;
}

function formatPercent(value: number | null | undefined): string {
  return value == null ? "Unavailable" : `${Math.round(value)}%`;
}

function formatTime(value: string, timezone: string): string {
  return new Date(value).toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
    timeZone: timezone,
  });
}
