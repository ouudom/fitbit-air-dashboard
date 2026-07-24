"use client";

import { Card, Typography } from "@heroui/react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { AppAlert } from "@/components/ui/AppAlert";
import { AppButton } from "@/components/ui/AppButton";
import { AppTextField } from "@/components/ui/AppTextField";
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
  return (
    <main className="grid min-h-screen place-items-center p-6">
      <Card className="w-full max-w-md" aria-labelledby="auth-title">
        <Card.Header className="grid gap-2">
          <Typography
            className="uppercase tracking-[0.11em] text-accent"
            type="body-xs"
            weight="bold"
          >
            Private health companion
          </Typography>
          <Typography.Heading id="auth-title" level={1}>
            {setup ? "Set up LifeStats" : "Welcome back"}
          </Typography.Heading>
          <Card.Description>
            Local account protects dashboard. Google Health connects separately.
          </Card.Description>
        </Card.Header>
        <Card.Content>
          <form className="grid gap-4" onSubmit={submit}>
            {setup && (
              <AppTextField
                inputProps={{ autoComplete: "one-time-code", type: "password" }}
                isRequired
                label="Setup token"
                name="setupToken"
              />
            )}
            <AppTextField
              inputProps={{ autoComplete: "email", type: "email" }}
              isRequired
              label="Email"
              name="email"
            />
            <AppTextField
              inputProps={{
                autoComplete: setup ? "new-password" : "current-password",
                minLength: 12,
                type: "password",
              }}
              isRequired
              label="Password"
              name="password"
            />
            {mutation.error && <AppAlert message={mutation.error.message} title="Sign-in failed" />}
            <AppButton fullWidth isPending={mutation.isPending} type="submit">
              {mutation.isPending ? "Working…" : setup ? "Create private account" : "Sign in"}
            </AppButton>
          </form>
        </Card.Content>
        <Card.Footer>
          <AppButton onPress={() => setSetup(!setup)} tone="quiet">
            {setup ? "Use existing account" : "First installation?"}
          </AppButton>
        </Card.Footer>
      </Card>
    </main>
  );
}
