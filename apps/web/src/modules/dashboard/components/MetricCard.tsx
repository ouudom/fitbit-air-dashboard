import type { Dashboard } from "@/lib/types";

type Metric = Dashboard["metrics"][number];

export function MetricCard({ metric, onOpen }: { metric: Metric; onOpen?: () => void }) {
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

  if (onOpen) {
    return (
      <button className="metricCard metricCardButton" onClick={onOpen}>
        {content}
      </button>
    );
  }
  return <article className="metricCard">{content}</article>;
}

function availabilityText(metric: Metric): string {
  if (metric.value !== null) return "Available";
  if (metric.availability === "not-synced") return "Not synced";
  return metric.availability.replaceAll("-", " ");
}
