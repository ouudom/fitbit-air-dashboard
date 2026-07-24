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
  if (range === "week") result.setUTCDate(result.getUTCDate() - 6);
  if (range === "month") result.setUTCMonth(result.getUTCMonth() - 1);
  if (range === "quarter") result.setUTCMonth(result.getUTCMonth() - 3);
  if (range === "year") result.setUTCFullYear(result.getUTCFullYear() - 1);
  return result.toISOString().slice(0, 10);
}

export function rangeLabel(insights: Insights): string {
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

function parseDate(value: string): Date {
  return new Date(`${value}T12:00:00Z`);
}
