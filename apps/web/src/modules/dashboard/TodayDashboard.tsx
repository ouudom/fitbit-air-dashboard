"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api";
import type { Dashboard } from "@/lib/types";
import { BatcaveOverview } from "./views/BatcaveOverview";
import { DashboardShell, type DashboardView } from "./layout/DashboardShell";
import { StasisArchitecture } from "./views/StasisArchitecture";

const today = () => new Date().toLocaleDateString("en-CA");

export function TodayDashboard({ email }: { email: string }) {
  const client = useQueryClient();
  const [activeView, setActiveView] = useState<DashboardView>("overview");
  const [date, setDate] = useState(today);
  const dashboard = useQuery({
    queryKey: ["dashboard", date],
    queryFn: () => api<Dashboard>(`/dashboard?date=${date}`),
  });
  const sync = useMutation({
    mutationFn: () =>
      api<{ jobId: string }>("/sync", {
        method: "POST",
        body: JSON.stringify({ days: 30 }),
      }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["dashboard"] }),
  });
  const logout = useMutation({
    mutationFn: () => api<void>("/auth/logout", { method: "POST" }),
    onSuccess: () => {
      client.clear();
      location.reload();
    },
  });

  const data = dashboard.data;
  const lastSync = data?.sync
    .map((item) => item.lastSyncedAt)
    .filter((value): value is string => Boolean(value))
    .sort()
    .at(-1);
  const syncLabel = sync.isPending
    ? "Syncing"
    : lastSync
      ? `Synced ${new Date(lastSync).toLocaleDateString([], { month: "short", day: "numeric" })}`
      : "Not synced";

  return (
    <DashboardShell
      activeView={activeView}
      email={email}
      logoutPending={logout.isPending}
      onLogout={() => logout.mutate()}
      onNavigate={setActiveView}
      syncLabel={syncLabel}
    >
      {dashboard.isPending && (
        <section className="contentState" aria-live="polite">
          <span className="spinner" aria-hidden="true" />
          <p>Loading Google Health data…</p>
        </section>
      )}

      {dashboard.isError && (
        <section className="contentState" role="alert">
          <span className="stateIcon">!</span>
          <h1>Dashboard unavailable</h1>
          <p>{dashboard.error.message}</p>
          <button className="secondaryButton" onClick={() => dashboard.refetch()}>
            Try again
          </button>
        </section>
      )}

      {data && activeView === "overview" && (
        <BatcaveOverview
          data={data}
          date={date}
          onDateChange={setDate}
          onOpenSleep={() => setActiveView("sleep")}
          onSync={() => sync.mutate()}
          syncError={sync.error?.message}
          syncing={sync.isPending}
        />
      )}

      {data && activeView === "sleep" && (
        <StasisArchitecture data={data} date={date} onDateChange={setDate} />
      )}
    </DashboardShell>
  );
}
