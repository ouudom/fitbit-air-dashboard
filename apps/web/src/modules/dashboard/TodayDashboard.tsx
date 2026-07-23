"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api";
import type { Dashboard } from "@/lib/types";
import { DashboardShell, type DashboardView } from "./layout/DashboardShell";
import { SleepOverview } from "./views/SleepOverview";
import { TodayOverview } from "./views/TodayOverview";

type IntegrationStatus = {
  connected: boolean;
  status: string;
};

export function TodayDashboard({ email, view }: { email: string; view: DashboardView }) {
  const client = useQueryClient();
  const [date, setDate] = useState<string>();
  const dashboard = useQuery({
    queryKey: ["dashboard", date ?? "current"],
    queryFn: () => api<Dashboard>(date ? `/dashboard?date=${date}` : "/dashboard"),
    refetchInterval: (query) => {
      const data = query.state.data;
      return data?.sync.some((item) => item.status === "queued" || item.status === "running")
        ? 5_000
        : false;
    },
  });
  const integration = useQuery({
    queryKey: ["google-health-integration"],
    queryFn: () => api<IntegrationStatus>("/integrations/google-health"),
  });
  const sync = useMutation({
    mutationFn: () =>
      api<{ status: string; dataTypes: string[] }>("/sync", {
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
  const selectedDate = date ?? data?.date ?? "";
  const syncRunning = data?.sync.some(
    (item) => item.status === "queued" || item.status === "running",
  );
  const lastSync = data?.sync
    .map((item) => item.lastSyncedAt)
    .filter((value): value is string => Boolean(value))
    .sort()
    .at(-1);
  const syncLabel = sync.isPending || syncRunning
    ? "Syncing"
    : lastSync
      ? `Synced ${new Date(lastSync).toLocaleDateString([], {
          month: "short",
          day: "numeric",
          timeZone: data?.timezone,
        })}`
      : "Not synced";

  return (
    <DashboardShell
      activeView={view}
      email={email}
      logoutPending={logout.isPending}
      onLogout={() => logout.mutate()}
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

      {data && view === "overview" && (
        <TodayOverview
          connected={integration.data?.connected ?? false}
          connectionLoading={integration.isPending}
          data={data}
          date={selectedDate}
          onDateChange={setDate}
          onSync={() => sync.mutate()}
          syncError={sync.error?.message}
          syncing={sync.isPending || Boolean(syncRunning)}
        />
      )}

      {data && view === "sleep" && (
        <SleepOverview data={data} date={selectedDate} onDateChange={setDate} />
      )}
    </DashboardShell>
  );
}
