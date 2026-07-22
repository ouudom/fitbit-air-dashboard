import Link from "next/link";
import type { Dashboard } from "@/lib/types";

type Metric = Dashboard["metrics"][number];

export function MetricCard({ metric, href }: { metric: Metric; href?: string }) {
  const content = (
    <>
      <div className="metricCardHeader">
        <span>{metric.label}</span>
        <i className={`availability availability-${metric.availability}`}>{availabilityText(metric)}</i>
      </div>
      <strong className="metricValue">
        {metric.value ?? "—"}
        {metric.value !== null && <small>{metric.unit}</small>}
      </strong>
      <p>{metric.value === null ? "No value synced for selected day" : metric.observedAt}</p>
      <footer>
        <span>{metric.source}</span>
        <span>{metric.freshness}</span>
      </footer>
    </>
  );

  if (href) {
    return (
      <Link className="metricCard metricCardButton" href={href}>
        {content}
      </Link>
    );
  }
  return <article className="metricCard">{content}</article>;
}

function availabilityText(metric: Metric): string {
  if (metric.value !== null) return "Available";
  if (metric.availability === "not-synced") return "Not synced";
  return metric.availability.replaceAll("-", " ");
}
