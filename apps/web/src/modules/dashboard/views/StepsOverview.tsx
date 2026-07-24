"use client";

import { Card, Chip, Spinner, Surface, Typography } from "@heroui/react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { EvilAnimatedBarChart } from "@/components/charts/EvilCharts";
import { AppAlert } from "@/components/ui/AppAlert";
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
  emptyChartSeries,
  insightsPath,
  type RangeKey,
  rangeLabel,
} from "../insights";

export function StepsOverview({ date }: { date: string }) {
  const [range, setRange] = useState<RangeKey>("week");
  const [endDate, setEndDate] = useState(date);
  const insights = useQuery({
    queryKey: ["insights", range, endDate],
    queryFn: () => api<Insights>(insightsPath(endDate, range)),
  });
  const points = insights.data?.steps ?? [];
  const buckets = insights.data?.stepBuckets ?? [];
  const values = points.map((point) => point.value);
  const total = values.reduce((sum, value) => sum + value, 0);
  const average = values.length ? Math.round(total / values.length) : null;
  const hasTimeBuckets = range === "day" && buckets.length > 0;
  const chartPoints =
    insights.data && displaysMissingDays(range)
      ? completeDailySeries(points, insights.data.start, insights.data.end)
      : points;
  const chartData = hasTimeBuckets
    ? buckets.map((point) => ({
          label: new Date(point.startedAt).toLocaleTimeString([], {
            hour: "numeric",
            timeZone: insights.data?.timezone,
          }),
          value: point.value,
          detail: new Date(point.startedAt).toLocaleString([], {
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
      <PageHeader title="Steps" />

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
        <AppAlert message={insights.error.message} title="Step history unavailable" />
      )}
      {insights.data && (
        <>
          <Card variant="default" aria-labelledby="steps-chart-title">
            <Card.Header>
              <SectionHeader
                action={
                  <Chip color="success" size="sm" variant="soft">
                    <Chip.Label>{insights.data.freshness}</Chip.Label>
                  </Chip>
                }
                eyebrow={rangeLabel(insights.data)}
                id="steps-chart-title"
                title={hasTimeBuckets ? "Steps by time" : "Steps over time"}
              />
            </Card.Header>
            <Card.Content className="grid gap-6">
              <div className="flex flex-wrap items-end gap-x-8 gap-y-3">
                <SummaryValue
                  label={range === "day" ? "total steps" : "steps per recorded day"}
                  value={formatNumber(range === "day" ? total : average)}
                />
                {range !== "day" && (
                  <div className="pb-1 text-sm text-muted">
                    {formatNumber(total)} total · {values.length} recorded days
                  </div>
                )}
              </div>
              <EvilAnimatedBarChart
                data={
                  chartData.length
                    ? chartData
                    : emptyChartSeries(insights.data.start, insights.data.end, range)
                }
                emptyMessage={
                  points.length || hasTimeBuckets ? undefined : "No step data in this range"
                }
                formatValue={formatNumber}
                valueLabel="steps"
              />
            </Card.Content>
          </Card>

          {/* <Surface className="flex flex-wrap justify-between gap-2 p-4" variant="tertiary">
            <Typography color="muted" type="body-xs">
              {insights.data.source} · {insights.data.derivation}
            </Typography>
            <Typography color="muted" type="body-xs">
              Missing days are not treated as zero.
            </Typography>
          </Surface> */}
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

function formatNumber(value: number | null): string {
  return value == null ? "—" : Math.round(value).toLocaleString();
}
