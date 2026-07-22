"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api";
import type { Dashboard } from "@/lib/types";

const today = () => new Date().toLocaleDateString("en-CA");

export function TodayDashboard({ email }: { email: string }) {
  const client = useQueryClient();
  const [date, setDate] = useState(today);
  const dashboard = useQuery({ queryKey: ["dashboard", date], queryFn: () => api<Dashboard>(`/dashboard?date=${date}`) });
  const sync = useMutation({
    mutationFn: () => api<{ jobId: string }>("/sync", { method: "POST", body: JSON.stringify({ days: 30 }) }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["dashboard"] }),
  });
  const logout = useMutation({
    mutationFn: () => api<void>("/auth/logout", { method: "POST" }),
    onSuccess: () => { client.clear(); location.reload(); },
  });
  if (dashboard.isPending) return <main className="center">Loading Today…</main>;
  if (dashboard.isError) return <main className="center"><p role="alert">{dashboard.error.message}</p></main>;
  const data = dashboard.data;
  const lastSync = data.sync.map((item) => item.lastSyncedAt).filter(Boolean).sort().at(-1);
  return <div className="appShell">
    <header className="topbar"><a className="brand" href="#top">LifeStats</a><nav aria-label="Primary"><a aria-current="page" href="#top">Today</a></nav><div className="account"><span>{email}</span><button className="textButton" onClick={() => logout.mutate()}>Sign out</button></div></header>
    <main id="top" className="page">
      <section className="intro"><div><p className="eyebrow">Google Health companion</p><h1>Today</h1><p className="muted">Sleep, movement, personal estimates, and daily logs.</p></div><div className="actions"><input aria-label="Dashboard date" type="date" value={date} onChange={(event) => setDate(event.target.value)} /><a className="button" href="/api/v1/integrations/google-health/connect">Connect Google Health</a><button className="primary" onClick={() => sync.mutate()} disabled={sync.isPending}>{sync.isPending ? "Queued…" : "Sync"}</button></div></section>
      {sync.error && <p className="error" role="alert">{sync.error.message}</p>}
      <section aria-labelledby="signals"><div className="sectionHead"><div><h2 id="signals">Daily signals</h2><p>Source and availability remain visible.</p></div></div><div className="metricGrid">
        {data.metrics.map((metric) => <article className="metricCard" key={metric.key}><small>{metric.label}</small><strong>{metric.value ?? "—"}<span>{metric.value !== null ? ` ${metric.unit}` : ""}</span></strong><p>{metric.value === null ? "Not synced" : metric.observedAt}</p><footer>{metric.source} · {metric.freshness}</footer></article>)}
        {data.scores.map((score) => <article className="metricCard score" key={score.key}><small>{score.label}</small><strong>{score.value ?? "—"}<span>{score.value !== null ? " / 100" : ""}</span></strong><p>{score.explanation}</p><footer title={score.disclaimer}>{score.modelVersion} · {score.status}</footer></article>)}
      </div></section>
      <section className="panel" aria-labelledby="timeline"><div className="sectionHead"><div><h2 id="timeline">Timeline</h2><p>Google Health activity and logs.</p></div></div>{data.timeline.length ? <ol className="timeline">{data.timeline.map((item) => <li key={item.id}><time dateTime={item.occurredAt}>{new Date(item.occurredAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</time><div><strong>{item.title}</strong><p>{item.detail ?? item.kind}</p></div><span>{item.source}</span></li>)}</ol> : <p className="empty">No events for this day.</p>}</section>
      <section className="panel source"><div><h2>Source status</h2><p>Local rows are rebuildable projections. Google Health remains health source of truth.</p></div><div><strong>{lastSync ? `Last synced ${new Date(lastSync).toLocaleString()}` : "Never synced"}</strong><p>{data.sync.filter((item) => item.status === "error").length ? `${data.sync.filter((item) => item.status === "error").length} data types need attention` : "No sync errors"}</p></div></section>
    </main>
  </div>;
}
