"use client";

import { useQuery } from "@tanstack/react-query";
import { AuthScreen } from "@/modules/identity/AuthScreen";
import { TodayDashboard } from "@/modules/dashboard/TodayDashboard";
import { api, ApiError } from "@/lib/api";
import type { Session } from "@/lib/types";

export default function Home() {
  const session = useQuery({ queryKey: ["session"], queryFn: () => api<Session>("/session") });
  if (session.isPending) return <main className="center"><div className="loader" role="status">Loading LifeStats…</div></main>;
  if (session.error instanceof ApiError && session.error.status === 401) return <AuthScreen />;
  if (session.isError) return <main className="center"><p role="alert">{session.error.message}</p></main>;
  return <TodayDashboard email={session.data.user.email} />;
}
