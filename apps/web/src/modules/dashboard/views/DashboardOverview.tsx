import { buttonVariants, Card, Chip, Typography } from "@heroui/react";
import { AppAlert } from "@/components/ui/AppAlert";
import { AppButton } from "@/components/ui/AppButton";
import { EmptyContent } from "@/components/ui/EmptyContent";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionHeader } from "@/components/ui/SectionHeader";
import type { Dashboard } from "@/lib/types";
import { MetricCard } from "../components/MetricCard";

type DashboardOverviewProps = {
  connected: boolean;
  connectionLoading: boolean;
  data: Dashboard;
  onSync: () => void;
  syncError?: string;
  syncing: boolean;
};

export function DashboardOverview({
  connected,
  connectionLoading,
  data,
  onSync,
  syncError,
  syncing,
}: DashboardOverviewProps) {
  return (
    <div className="mx-auto grid w-full max-w-6xl gap-6">
      <PageHeader
        actions={
          <>
            {!connectionLoading && !connected && (
              <a
                className={buttonVariants({ variant: "secondary" })}
                href="/api/v1/integrations/google-health/connect"
              >
                Connect Google Health
              </a>
            )}
            <AppButton
              isDisabled={syncing || !connected}
              isPending={syncing}
              onPress={onSync}
            >
              <span className={`text-lg leading-none ${syncing ? "animate-spin" : ""}`} aria-hidden="true">
                ↻
              </span>
              {syncing ? "Syncing…" : connected ? "Sync data" : "Connect to sync"}
            </AppButton>
          </>
        }
        title="Dashboard"
      />

      {syncError && <AppAlert message={syncError} title="Sync failed" />}

      <section aria-label="Daily health signals">
        <div className="grid grid-cols-4 gap-3 max-xl:grid-cols-2 max-sm:grid-cols-1">
          {data.metrics.map((metric) => (
            <MetricCard
              href={metric.key === "sleep" ? "/sleep" : undefined}
              key={metric.key}
              metric={metric}
            />
          ))}
        </div>
      </section>

      <Card variant="secondary" aria-labelledby="timeline-title">
        <Card.Header>
          <SectionHeader
            action={
              <Chip size="sm" variant="soft">
                <Chip.Label>{data.timeline.length} events</Chip.Label>
              </Chip>
            }
            id="timeline-title"
            title="Health timeline"
          />
        </Card.Header>
        <Card.Content>
          {data.timeline.length ? (
            <ol className="grid">
              {data.timeline.map((item) => (
                <li
                  className="grid grid-cols-[12px_64px_minmax(0,1fr)_auto] items-start gap-3 border-b border-separator py-3 last:border-0 max-sm:grid-cols-[12px_minmax(0,1fr)]"
                  key={item.id}
                >
                  <span className="mt-1.5 size-2 rounded-full bg-accent" aria-hidden="true" />
                  <time className="text-xs tabular-nums text-muted" dateTime={item.occurredAt}>
                    {new Date(item.occurredAt).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                      timeZone: data.timezone,
                    })}
                  </time>
                  <div className="min-w-0">
                    <Typography weight="semibold">{item.title}</Typography>
                    <Typography.Paragraph color="muted" size="xs">
                      {item.detail ?? item.kind}
                    </Typography.Paragraph>
                  </div>
                  <Chip className="max-sm:col-start-2" size="sm" variant="tertiary">
                    <Chip.Label>{item.source}</Chip.Label>
                  </Chip>
                </li>
              ))}
            </ol>
          ) : (
            <EmptyContent
              description="Sync Google Health or select another date."
              title="No events for this day"
            />
          )}
        </Card.Content>
      </Card>
    </div>
  );
}
