"use client";

import { useQuery } from "@tanstack/react-query";
import { ApiError, api } from "@/lib/api";
import type { Session } from "@/lib/types";
import { AuthScreen } from "@/modules/identity/AuthScreen";
import type { DashboardView } from "./layout/DashboardShell";
import { TodayDashboard } from "./TodayDashboard";

export function DashboardRoute({ view }: { view: DashboardView }) {
  const session = useQuery({
    queryKey: ["session"],
    queryFn: () => api<Session>("/session"),
  });

  if (session.isPending) {
    return (
      <main className="center">
        <div className="loader" role="status">
          Loading LifeStats…
        </div>
      </main>
    );
  }
  if (session.error instanceof ApiError && session.error.status === 401) return <AuthScreen />;
  if (session.isError) {
    return (
      <main className="center">
        <p role="alert">{session.error.message}</p>
      </main>
    );
  }
  return <TodayDashboard email={session.data.user.email} view={view} />;
}
