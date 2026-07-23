"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { api } from "@/lib/api";
import type { Session } from "@/lib/types";

export function AuthScreen() {
  const client = useQueryClient();
  const [setup, setSetup] = useState(false);
  const mutation = useMutation({
    mutationFn: (body: Record<string, string>) => api<Session>(setup ? "/setup" : "/auth/login", {
      method: "POST", body: JSON.stringify(body),
    }),
    onSuccess: (session) => { client.setQueryData(["session"], session); },
  });
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    mutation.mutate({
      email: String(form.get("email")), password: String(form.get("password")),
      ...(setup ? { setup_token: String(form.get("setupToken")) } : {}),
    });
  }
  return <main className="authPage"><section className="authPanel" aria-labelledby="auth-title">
    <p className="eyebrow">Private health companion</p>
    <h1 id="auth-title">{setup ? "Set up LifeStats" : "Welcome back"}</h1>
    <p className="muted">Local account protects dashboard. Google Health connects separately.</p>
    <form onSubmit={submit} className="stack">
      {setup && <label>Setup token<input name="setupToken" type="password" required autoComplete="one-time-code" /></label>}
      <label>Email<input name="email" type="email" required autoComplete="email" /></label>
      <label>Password<input name="password" type="password" minLength={12} required autoComplete={setup ? "new-password" : "current-password"} /></label>
      {mutation.error && <p className="error" role="alert">{mutation.error.message}</p>}
      <button className="primary" disabled={mutation.isPending}>{mutation.isPending ? "Working…" : setup ? "Create private account" : "Sign in"}</button>
    </form>
    <button className="textButton" onClick={() => setSetup(!setup)}>{setup ? "Use existing account" : "First installation?"}</button>
  </section></main>;
}
