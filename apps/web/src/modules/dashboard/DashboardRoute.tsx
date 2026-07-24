"use client";

import { Spinner } from "@heroui/react";
import { useQuery } from "@tanstack/react-query";
import { AppAlert } from "@/components/ui/AppAlert";
import { ApiError, api } from "@/lib/api";
import type { Session } from "@/lib/types";
import { AuthScreen } from "@/modules/auth/AuthScreen";
import { Dashboard } from "./Dashboard";
import type { DashboardView } from "./layout/DashboardShell";

export function DashboardRoute({ view }: { view: DashboardView }) {
  const session = useQuery({
    queryKey: ["session"],
    queryFn: () => api<Session>("/session"),
  });

  if (session.isPending) {
    return (
      <main className="grid min-h-screen place-items-center">
        <div className="grid justify-items-center gap-3" role="status">
          <Spinner color="accent" size="lg" />
          <p className="text-sm text-muted">Loading LifeStats…</p>
        </div>
      </main>
    );
  }
  if (session.error instanceof ApiError && session.error.status === 401) return <AuthScreen />;
  if (session.isError) {
    return (
      <main className="grid min-h-screen place-items-center p-6">
        <div className="w-full max-w-lg">
          <AppAlert message={session.error.message} title="LifeStats unavailable" />
        </div>
      </main>
    );
  }
  return <Dashboard email={session.data.user.email} view={view} />;
}
