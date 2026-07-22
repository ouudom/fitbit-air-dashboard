"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { api } from "@/lib/api";
import type { Dashboard, Habit } from "@/lib/types";

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
      <div className="twoColumn"><HabitPanel habits={data.habits} date={date} onChange={() => client.invalidateQueries({ queryKey: ["dashboard", date] })} /><section className="panel" aria-labelledby="timeline"><div className="sectionHead"><div><h2 id="timeline">Timeline</h2><p>Google Health and LifeStats logs.</p></div></div>{data.timeline.length ? <ol className="timeline">{data.timeline.map((item) => <li key={item.id}><time dateTime={item.occurredAt}>{new Date(item.occurredAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</time><div><strong>{item.title}</strong><p>{item.detail ?? item.kind}</p></div><span>{item.source}</span></li>)}</ol> : <p className="empty">No events for this day.</p>}</section></div>
      <section className="panel source"><div><h2>Source status</h2><p>Local rows are rebuildable projections. Google Health remains health source of truth.</p></div><div><strong>{lastSync ? `Last synced ${new Date(lastSync).toLocaleString()}` : "Never synced"}</strong><p>{data.sync.filter((item) => item.status === "error").length ? `${data.sync.filter((item) => item.status === "error").length} data types need attention` : "No sync errors"}</p></div></section>
    </main>
  </div>;
}

function HabitPanel({ habits, date, onChange }: { habits: Habit[]; date: string; onChange: () => void }) {
  const [creating, setCreating] = useState(false);
  const mutation = useMutation({ mutationFn: ({ path, body, method = "POST" }: { path: string; body?: object; method?: string }) => api(path, { method, body: body ? JSON.stringify(body) : undefined }), onSuccess: () => { setCreating(false); onChange(); } });
  function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = new FormData(event.currentTarget); const numeric = form.get("targetType") === "numeric";
    const weekdays = form.getAll("weekday").map(Number);
    mutation.mutate({ path: "/habits", body: { title: form.get("title"), kind: form.get("kind"), target_type: form.get("targetType"), target_value: numeric ? Number(form.get("targetValue")) : null, unit: numeric ? form.get("unit") : null, weekdays } });
  }
  function log(habit: Habit, value: number) { mutation.mutate({ path: `/habits/${habit.id}/entries`, body: { occurred_at: new Date(`${date}T12:00:00`).toISOString(), value } }); }
  function edit(habit: Habit) { const title = window.prompt("Habit name", habit.title)?.trim(); if (title && title !== habit.title) mutation.mutate({ path: `/habits/${habit.id}`, method: "PATCH", body: { title } }); }
  function archive(habit: Habit) { if (window.confirm(`Archive ${habit.title}?`)) mutation.mutate({ path: `/habits/${habit.id}`, method: "DELETE" }); }
  return <section className="panel" aria-labelledby="habits"><div className="sectionHead"><div><h2 id="habits">Habits</h2><p>Scheduled for selected day.</p></div><button className="button" onClick={() => setCreating(!creating)}>Add habit</button></div>
    {creating && <form className="habitForm" onSubmit={create}><label>Name<input name="title" required maxLength={120} /></label><label>Storage<select name="kind"><option value="local">LifeStats</option><option value="google_hydration">Google hydration</option><option value="google_weight">Google weight</option></select></label><label>Target<select name="targetType"><option value="boolean">Yes / no</option><option value="numeric">Number</option></select></label><label>Amount<input name="targetValue" type="number" min="0.01" step="any" /></label><label>Unit<input name="unit" placeholder="ml, kg, min" /></label><fieldset><legend>Schedule</legend>{["Mon","Tue","Wed","Thu","Fri","Sat","Sun"].map((label, day) => <label key={label}><input name="weekday" type="checkbox" value={day} defaultChecked />{label}</label>)}</fieldset><button className="primary">Save</button></form>}
    {mutation.error && <p className="error" role="alert">{mutation.error.message}</p>}
    {habits.length ? <ul className="habitList">{habits.map((habit) => <li key={habit.id}><div><strong>{habit.title}</strong><p>{habit.progress} {habit.unit ?? ""} / {habit.targetValue ?? 1} {habit.unit ?? ""}</p></div><div className="habitActions">{habit.targetType === "boolean" ? <button disabled={habit.complete || mutation.isPending} onClick={() => log(habit, 1)}>{habit.complete ? "Done" : "Complete"}</button> : <NumericLog habit={habit} onLog={(value) => log(habit, value)} />}<button className="textButton" aria-label={`Edit ${habit.title}`} onClick={() => edit(habit)}>Edit</button><button className="textButton" aria-label={`Archive ${habit.title}`} onClick={() => archive(habit)}>Archive</button></div></li>)}</ul> : <p className="empty">No habits scheduled.</p>}
  </section>;
}

function NumericLog({ habit, onLog }: { habit: Habit; onLog: (value: number) => void }) {
  const [value, setValue] = useState("");
  return <div className="numericLog"><input aria-label={`Value for ${habit.title}`} type="number" step="any" value={value} onChange={(event) => setValue(event.target.value)} /><button disabled={!value} onClick={() => { onLog(Number(value)); setValue(""); }}>Log</button></div>;
}
