import { Card, Chip, Typography } from "@heroui/react";
import Link from "next/link";
import { formatSleepDuration } from "@/lib/format";
import type { Dashboard } from "@/lib/types";

type Metric = Dashboard["metrics"][number];

export function MetricCard({ metric, href }: { metric: Metric; href?: string }) {
  const card = (
    <Card
      className={`h-full min-h-44 ${href ? "transition-transform hover:-translate-y-0.5" : ""}`}
      variant="secondary"
    >
      <Card.Header className="flex items-start justify-between gap-3">
        <Card.Title className="text-sm">{metric.label}</Card.Title>
        <Chip color={metric.value !== null ? "success" : "warning"} size="sm" variant="soft">
          <Chip.Label>{availabilityText(metric)}</Chip.Label>
        </Chip>
      </Card.Header>
      <Card.Content className="grid content-start gap-2">
        <Typography className="text-3xl tabular-nums" weight="bold">
          {metric.value === null
            ? "—"
            : metric.key === "sleep"
              ? formatSleepDuration(metric.value)
              : metric.value}
          {metric.value !== null && metric.key !== "sleep" && (
            <span className="ml-1.5 text-xs font-medium text-muted">{metric.unit}</span>
          )}
        </Typography>
        <Typography.Paragraph color="muted" size="xs">
          {metric.value === null ? "No value synced for selected day" : metric.observedAt}
        </Typography.Paragraph>
      </Card.Content>
      <Card.Footer className="mt-auto flex justify-between gap-3 text-xs text-muted">
        <span>{metric.source}</span>
        <span>{metric.freshness}</span>
      </Card.Footer>
    </Card>
  );

  return href ? (
    <Link
      className="rounded-xl focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-accent"
      href={href}
    >
      {card}
    </Link>
  ) : (
    <article>{card}</article>
  );
}

function availabilityText(metric: Metric): string {
  if (metric.value !== null) return "Available";
  if (metric.availability === "not-synced") return "Not synced";
  return metric.availability.replaceAll("-", " ");
}
