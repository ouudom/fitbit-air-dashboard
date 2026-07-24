"use client";

import { Card, Chip, Spinner, Surface, Typography } from "@heroui/react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { EvilAnimatedBarChart } from "@/components/charts/EvilCharts";
import { AppAlert } from "@/components/ui/AppAlert";
import { EmptyContent } from "@/components/ui/EmptyContent";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { api } from "@/lib/api";
import type { Insights } from "@/lib/types";
import {
  completeDailySeries,
  calendarRangeEnd,
  DateRangeControls,
  dateTick,
  displaysMissingDays,
  insightsPath,
  type RangeKey,
  rangeLabel,
} from "../insights";

export function WaterIntakeOverview({ date }: { date: string }) {
  const [range, setRange] = useState<RangeKey>("week");
  const [endDate, setEndDate] = useState(date);
  const insights = useQuery({
    queryKey: ["insights", range, endDate],
    queryFn: () => api<Insights>(insightsPath(endDate, range)),
  });
  const points = insights.data?.water ?? [];
  const dayEntries =
    insights.data?.waterEntries.filter(
      (entry) =>
        new Date(entry.startedAt).toLocaleDateString("en-CA", {
          timeZone: insights.data?.timezone,
        }) === endDate,
    ) ?? [];
  const values = points.map((point) => point.value);
  const total = values.reduce((sum, value) => sum + value, 0);
  const average = values.length ? total / values.length : null;
  const chartPoints =
    insights.data && displaysMissingDays(range)
      ? completeDailySeries(points, insights.data.start, insights.data.end)
      : points;
  const chartData =
    range === "day"
      ? dayEntries.map((entry) => ({
          label: new Date(entry.startedAt).toLocaleTimeString([], {
            hour: "numeric",
            minute: "2-digit",
            timeZone: insights.data?.timezone,
          }),
          value: entry.value,
          detail: new Date(entry.startedAt).toLocaleString([], {
            dateStyle: "medium",
            timeStyle: "short",
            timeZone: insights.data?.timezone,
          }),
        }))
      : chartPoints.map((point) => ({
          label: dateTick(point.date, range),
          value: point.value,
          detail: new Date(`${point.date}T12:00:00Z`).toLocaleDateString([], {
            dateStyle: "full",
          }),
        }));

  return (
    <div className="mx-auto grid w-full max-w-6xl gap-6">
      <PageHeader title="Water intake" />

      <DateRangeControls
        end={endDate}
        max={date}
        onEndChange={setEndDate}
        onRangeChange={(nextRange) => {
          setRange(nextRange);
          setEndDate(calendarRangeEnd(endDate, nextRange, date));
        }}
        range={range}
      />

      {insights.isPending && (
        <Card variant="secondary">
          <Card.Content className="grid min-h-80 place-items-center">
            <Spinner color="accent" size="lg" />
          </Card.Content>
        </Card>
      )}
      {insights.isError && (
        <AppAlert message={insights.error.message} title="Water history unavailable" />
      )}
      {insights.data && (
        <>
          <Card variant="default" aria-labelledby="water-chart-title">
            <Card.Header>
              <SectionHeader
                action={
                  <Chip color="success" size="sm" variant="soft">
                    <Chip.Label>{insights.data.freshness}</Chip.Label>
                  </Chip>
                }
                eyebrow={rangeLabel(insights.data)}
                id="water-chart-title"
                title={range === "day" ? "Water by time" : "Water over time"}
              />
            </Card.Header>
            <Card.Content className="grid gap-6">
              <div className="flex flex-wrap items-end gap-x-8 gap-y-3">
                <SummaryValue
                  label={range === "day" ? "ml total" : "ml per recorded day"}
                  value={formatMilliliters(range === "day" ? total : average)}
                />
                {range !== "day" && (
                  <div className="pb-1 text-sm text-muted">
                    {formatMilliliters(total)} ml total · {values.length} recorded days
                  </div>
                )}
              </div>
              {(range === "day" ? dayEntries.length : points.length) ? (
                <EvilAnimatedBarChart
                  data={chartData}
                  fill="var(--water)"
                  formatValue={formatMilliliters}
                  valueLabel="ml"
                />
              ) : (
                <EmptyContent
                  description="Sync Google Health or choose another date range."
                  title="No water data in this range"
                />
              )}
            </Card.Content>
          </Card>

          <Card variant="secondary" aria-labelledby="water-records-title">
            <Card.Header>
              <SectionHeader
                action={
                  <Chip size="sm" variant="tertiary">
                    <Chip.Label>
                      {range === "day" ? `${dayEntries.length} logs` : `${points.length} days`}
                    </Chip.Label>
                  </Chip>
                }
                id="water-records-title"
                title={range === "day" ? "Today" : "Daily water"}
              />
            </Card.Header>
            <Card.Content>
              {(range === "day" ? dayEntries : points).length ? (
                <ol className="grid">
                  {range === "day"
                    ? [...dayEntries].reverse().map((entry) => (
                        <li
                          className="flex items-center justify-between gap-4 border-b border-separator py-3 last:border-0"
                          key={`${entry.startedAt}-${entry.value}`}
                        >
                          <time className="text-sm text-muted" dateTime={entry.startedAt}>
                            {new Date(entry.startedAt).toLocaleTimeString([], {
                              hour: "numeric",
                              minute: "2-digit",
                              timeZone: insights.data.timezone,
                            })}
                          </time>
                          <Typography className="tabular-nums" weight="semibold">
                            {formatMilliliters(entry.value)} ml
                          </Typography>
                        </li>
                      ))
                    : [...points].reverse().slice(0, 14).map((point) => (
                        <li
                          className="flex items-center justify-between gap-4 border-b border-separator py-3 last:border-0"
                          key={point.date}
                        >
                          <time className="text-sm text-muted" dateTime={point.date}>
                            {new Date(`${point.date}T12:00:00Z`).toLocaleDateString([], {
                              day: "numeric",
                              month: "short",
                              weekday: "short",
                            })}
                          </time>
                          <Typography className="tabular-nums" weight="semibold">
                            {formatMilliliters(point.value)} ml
                          </Typography>
                        </li>
                      ))}
                </ol>
              ) : (
                <EmptyContent
                  description="Google Health has no hydration logs for this range."
                  title="No recorded water"
                />
              )}
            </Card.Content>
          </Card>

          <Surface className="flex flex-wrap justify-between gap-2 p-4" variant="tertiary">
            <Typography color="muted" type="body-xs">
              {insights.data.source} · {insights.data.derivation}
            </Typography>
            <Typography color="muted" type="body-xs">
              Missing days are not treated as zero. No intake goal is inferred.
            </Typography>
          </Surface>
        </>
      )}
    </div>
  );
}

function SummaryValue({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="text-5xl font-bold tracking-[-0.04em] tabular-nums max-sm:text-4xl">
        {value}
      </span>
      <span className="ml-2 text-sm font-semibold text-muted">{label}</span>
    </div>
  );
}

function formatMilliliters(value: number | null): string {
  return value == null ? "—" : Math.round(value).toLocaleString();
}
