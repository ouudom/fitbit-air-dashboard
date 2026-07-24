import { CalendarDays, ChevronLeft, ChevronRight } from "lucide-react";
import type { Insights } from "@/lib/types";

export type RangeKey = "day" | "week" | "month" | "quarter" | "year";

export const RANGE_OPTIONS: Array<{ key: RangeKey; label: string }> = [
  { key: "day", label: "D" },
  { key: "week", label: "W" },
  { key: "month", label: "M" },
  { key: "quarter", label: "3M" },
  { key: "year", label: "Y" },
];

export function insightsPath(end: string, range: RangeKey): string {
  return `/insights?start=${rangeStart(end, range)}&end=${end}`;
}

export function rangeStart(end: string, range: RangeKey): string {
  const result = parseDate(end);
  if (range === "week") {
    const daysSinceMonday = (result.getUTCDay() + 6) % 7;
    result.setUTCDate(result.getUTCDate() - daysSinceMonday);
  }
  if (range === "month") result.setUTCDate(1);
  if (range === "quarter") {
    result.setUTCMonth(Math.floor(result.getUTCMonth() / 3) * 3, 1);
  }
  if (range === "year") result.setUTCMonth(0, 1);
  return result.toISOString().slice(0, 10);
}

export function rangeLabel(insights: Pick<Insights, "start" | "end">): string {
  const start = parseDate(insights.start);
  const end = parseDate(insights.end);
  const startLabel = start.toLocaleDateString([], { day: "numeric", month: "short" });
  const endLabel = end.toLocaleDateString([], {
    day: "numeric",
    month: "short",
    year: start.getUTCFullYear() === end.getUTCFullYear() ? undefined : "numeric",
  });
  return insights.start === insights.end ? endLabel : `${startLabel}–${endLabel}`;
}

export function dateTick(value: string, range: RangeKey): string {
  const date = parseDate(value);
  if (range === "year") {
    return date.toLocaleDateString([], { month: "short" });
  }
  return date.toLocaleDateString([], {
    day: range === "day" ? undefined : "numeric",
    month: range === "day" ? undefined : "short",
    weekday: range === "week" ? "short" : undefined,
  });
}

export function completeDailySeries(
  points: Array<{ date: string; value: number }>,
  start: string,
  end: string,
): Array<{ date: string; value: number | null }> {
  const valuesByDate = new Map(points.map((point) => [point.date, point.value]));
  const cursor = parseDate(start);
  const last = parseDate(end);
  const series: Array<{ date: string; value: number | null }> = [];

  while (cursor <= last) {
    const date = cursor.toISOString().slice(0, 10);
    series.push({ date, value: valuesByDate.get(date) ?? null });
    cursor.setUTCDate(cursor.getUTCDate() + 1);
  }

  return series;
}

export function displaysMissingDays(range: RangeKey): boolean {
  return range === "week" || range === "month" || range === "quarter";
}

export function emptyChartSeries(
  start: string,
  end: string,
  range: RangeKey,
): Array<{ label: string; value: null }> {
  if (range === "day") {
    return ["12 AM", "6 AM", "12 PM", "6 PM"].map((label) => ({
      label,
      value: null,
    }));
  }

  if (range === "year") {
    const cursor = parseDate(start);
    const last = parseDate(end);
    const series: Array<{ label: string; value: null }> = [];
    while (cursor <= last) {
      series.push({
        label: cursor.toLocaleDateString([], { month: "short" }),
        value: null,
      });
      cursor.setUTCMonth(cursor.getUTCMonth() + 1, 1);
    }
    return series;
  }

  return completeDailySeries([], start, end).map((point) => ({
    label: dateTick(point.date, range),
    value: null,
  }));
}

export function RangeTabs({
  onChange,
  value,
}: {
  onChange: (range: RangeKey) => void;
  value: RangeKey;
}) {
  return (
    <div
      aria-label="Chart date range"
      className="grid grid-cols-5 gap-1 rounded-xl bg-[var(--surface-inset)] p-1"
      role="group"
    >
      {RANGE_OPTIONS.map((option) => (
        <button
          aria-pressed={value === option.key}
          className={`min-h-10 rounded-lg px-3 text-sm font-semibold transition-colors ${
            value === option.key
              ? "bg-[var(--info)] text-[var(--canvas)]"
              : "text-muted hover:bg-[var(--surface-raised)] hover:text-foreground"
          }`}
          key={option.key}
          onClick={() => onChange(option.key)}
          type="button"
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

export function DateRangeControls({
  end,
  max,
  onEndChange,
  onRangeChange,
  range,
}: {
  end: string;
  max: string;
  onEndChange: (end: string) => void;
  onRangeChange: (range: RangeKey) => void;
  range: RangeKey;
}) {
  const canMoveNext = end < max;

  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <RangeTabs onChange={onRangeChange} value={range} />
      <div className="flex flex-wrap items-center gap-2">
        <div
          aria-label="Chart period"
          className="flex min-h-12 items-stretch overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface-raised)]"
          role="group"
        >
          <button
            aria-label={`Previous ${range}`}
            className="grid min-w-11 place-items-center text-muted transition-colors hover:bg-[var(--surface-inset)] hover:text-foreground"
            onClick={() => onEndChange(adjacentRangeEnd(end, range, -1, max))}
            title={`Previous ${range}`}
            type="button"
          >
            <ChevronLeft aria-hidden="true" className="size-5" />
          </button>
          <label className="relative flex min-w-44 cursor-pointer items-center justify-center gap-2 border-x border-[var(--border)] px-4 text-sm font-semibold hover:bg-[var(--surface-inset)]">
            <CalendarDays aria-hidden="true" className="size-4 text-muted" />
            <span>{periodLabel(end, range)}</span>
            <input
              aria-label="Select chart end date"
              className="absolute inset-0 cursor-pointer opacity-0"
              max={max}
              onChange={(event) => {
                if (event.target.value) {
                  onEndChange(calendarRangeEnd(event.target.value, range, max));
                }
              }}
              type="date"
              value={end}
            />
          </label>
          <button
            aria-label={`Next ${range}`}
            className="grid min-w-11 place-items-center text-muted transition-colors enabled:hover:bg-[var(--surface-inset)] enabled:hover:text-foreground disabled:cursor-not-allowed disabled:opacity-40"
            disabled={!canMoveNext}
            onClick={() => onEndChange(adjacentRangeEnd(end, range, 1, max))}
            title={`Next ${range}`}
            type="button"
          >
            <ChevronRight aria-hidden="true" className="size-5" />
          </button>
        </div>
        <button
          className="min-h-12 rounded-xl border border-[var(--border-strong)] bg-[var(--surface-raised)] px-4 text-sm font-semibold text-muted transition-colors enabled:hover:bg-[var(--surface-inset)] enabled:hover:text-foreground disabled:cursor-default disabled:opacity-50"
          disabled={!canMoveNext}
          onClick={() => onEndChange(max)}
          type="button"
        >
          Current
        </button>
      </div>
    </div>
  );
}

export function calendarRangeEnd(value: string, range: RangeKey, max: string): string {
  if (range === "day") return minDate(value, max);

  const result = parseDate(rangeStart(value, range));
  if (range === "week") result.setUTCDate(result.getUTCDate() + 6);
  if (range === "month") result.setUTCMonth(result.getUTCMonth() + 1, 0);
  if (range === "quarter") result.setUTCMonth(result.getUTCMonth() + 3, 0);
  if (range === "year") result.setUTCFullYear(result.getUTCFullYear() + 1, 0, 0);
  return minDate(result.toISOString().slice(0, 10), max);
}

function adjacentRangeEnd(
  value: string,
  range: RangeKey,
  direction: -1 | 1,
  max: string,
): string {
  const result = parseDate(direction < 0 ? rangeStart(value, range) : value);
  result.setUTCDate(result.getUTCDate() + direction);
  return calendarRangeEnd(result.toISOString().slice(0, 10), range, max);
}

function periodLabel(end: string, range: RangeKey): string {
  const start = rangeStart(end, range);
  return rangeLabel({ start, end });
}

function minDate(first: string, second: string): string {
  return first < second ? first : second;
}

function parseDate(value: string): Date {
  return new Date(`${value}T12:00:00Z`);
}
