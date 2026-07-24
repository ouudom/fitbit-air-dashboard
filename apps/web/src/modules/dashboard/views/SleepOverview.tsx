import { Card, Chip, Surface, Typography } from "@heroui/react";
import { AppTextField } from "@/components/ui/AppTextField";
import { EmptyContent } from "@/components/ui/EmptyContent";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { formatSleepDuration } from "@/lib/format";
import type { Dashboard } from "@/lib/types";

export function SleepOverview({
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
        description="Sleep duration and session availability from the selected day."
        eyebrow="Google Health sleep"
        title="Sleep"
      />

      <Card variant="default" aria-labelledby="sleep-summary-title">
        <Card.Content className="grid grid-cols-[220px_minmax(0,1fr)] items-center gap-8 max-md:grid-cols-1">
          <Surface
            className="grid aspect-square w-52 place-items-center justify-self-center rounded-full text-center max-md:w-44"
            variant="tertiary"
            aria-label={
              sleep?.value != null
                ? `${formatSleepDuration(sleep.value)} asleep`
                : "Sleep duration unavailable"
            }
          >
            <div>
              <Typography className="block text-5xl tabular-nums" weight="bold">
                {sleep?.value != null ? formatSleepDuration(sleep.value) : "—"}
              </Typography>
              <Typography color="muted" type="body-sm">
                {sleep?.value != null ? "asleep" : "not synced"}
              </Typography>
            </div>
          </Surface>

          <div>
            <Typography
              className="mb-1.5 uppercase tracking-[0.1em] text-accent"
              type="body-xs"
              weight="bold"
            >
              Selected night
            </Typography>
            <Typography.Heading id="sleep-summary-title" level={2}>
              Sleep duration
            </Typography.Heading>
            <Typography.Paragraph className="mt-2 max-w-[60ch]" color="muted" size="sm">
              {sleep?.value != null
                ? `Google Health reported ${formatSleepDuration(sleep.value)} of sleep for ${sleep.observedAt}.`
                : "No sleep session has been synced for this date."}
            </Typography.Paragraph>
            <dl className="mt-6 grid grid-cols-3 gap-3 max-sm:grid-cols-1">
              {[
                ["Source", sleep?.source ?? "Google Health"],
                ["Freshness", sleep?.freshness ?? "unknown"],
                [
                  "Availability",
                  sleep?.availability.replaceAll("-", " ") ?? "not synced",
                ],
              ].map(([label, value]) => (
                <Surface className="grid gap-1 p-3" key={label} variant="tertiary">
                  <dt className="text-xs text-muted">{label}</dt>
                  <dd className="text-sm font-semibold capitalize">{value}</dd>
                </Surface>
              ))}
            </dl>
          </div>
        </Card.Content>
      </Card>

      <Card variant="secondary" aria-labelledby="architecture-title">
        <Card.Header>
          <SectionHeader
            action={
              <Chip color="warning" size="sm" variant="soft">
                <Chip.Label>Current API gap</Chip.Label>
              </Chip>
            }
            eyebrow="Sleep composition"
            id="architecture-title"
            title="Architecture details"
          />
        </Card.Header>
        <Card.Content>
          <div className="grid grid-cols-4 gap-3 max-xl:grid-cols-2 max-sm:grid-cols-1">
            {[
              ["Time in bed", "Not available"],
              ["Sleep stages", "Not available"],
              ["Sleep efficiency", "Not available"],
              ["Respiratory rate", "Not available"],
            ].map(([label, value]) => (
              <Surface className="grid gap-1.5 p-4" key={label} variant="tertiary">
                <Typography color="muted" type="body-xs">
                  {label}
                </Typography>
                <Typography weight="semibold">{value}</Typography>
                <Typography color="muted" type="body-xs">
                  Not exposed by current dashboard contract
                </Typography>
              </Surface>
            ))}
          </div>
        </Card.Content>
        <Card.Footer>
          <Typography.Paragraph color="muted" size="xs">
            LifeStats does not estimate missing sleep stages or present a local sleep score.
          </Typography.Paragraph>
        </Card.Footer>
      </Card>

      <Card variant="secondary" aria-labelledby="sessions-title">
        <Card.Header>
          <SectionHeader
            action={
              <Chip size="sm" variant="soft">
                <Chip.Label>{sessions.length} sessions</Chip.Label>
              </Chip>
            }
            eyebrow="Synced records"
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
                      {new Date(session.occurredAt).toLocaleString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                        month: "short",
                        day: "numeric",
                        timeZone: data.timezone,
                      })}
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
              description="Try syncing Google Health or selecting another date."
              icon="☾"
              title="No sleep session synced"
            />
          )}
        </Card.Content>
      </Card>
    </div>
  );
}
