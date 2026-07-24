"use client";

import { Card, Checkbox, Chip, Spinner, Surface, Typography } from "@heroui/react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { KeyRound } from "lucide-react";
import { type FormEvent, useState } from "react";
import { AppAlert } from "@/components/ui/AppAlert";
import { AppButton } from "@/components/ui/AppButton";
import { AppTextField } from "@/components/ui/AppTextField";
import { EmptyContent } from "@/components/ui/EmptyContent";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { api } from "@/lib/api";
import type { AgentScope, McpToken, IssuedMcpToken } from "@/lib/types";

type ScopeOption = {
  scope: AgentScope;
  label: string;
  detail: string;
  group: "Read access" | "Sensitive data" | "Actions";
};

const scopeOptions: ScopeOption[] = [
  {
    scope: "profile:read",
    label: "Profile",
    detail: "Display name and timezone",
    group: "Read access",
  },
  {
    scope: "today:read",
    label: "Dashboard",
    detail: "Daily metrics and timeline",
    group: "Read access",
  },
  {
    scope: "fitness:read",
    label: "Steps and activity",
    detail: "Activity, exercise, and trends",
    group: "Read access",
  },
  {
    scope: "sleep:read",
    label: "Sleep",
    detail: "Sleep sessions and trends",
    group: "Read access",
  },
  {
    scope: "health:read",
    label: "Health",
    detail: "Measurements excluding ECG and rhythm alerts",
    group: "Read access",
  },
  {
    scope: "nutrition:read",
    label: "Nutrition",
    detail: "Nutrition and hydration logs",
    group: "Read access",
  },
  {
    scope: "sync:read",
    label: "Sync status",
    detail: "Freshness and synchronization state",
    group: "Read access",
  },
  {
    scope: "integration:read",
    label: "Connection status",
    detail: "Google Health connection state",
    group: "Read access",
  },
  {
    scope: "ecg:read",
    label: "Electrocardiograms",
    detail: "Explicit access to ECG records",
    group: "Sensitive data",
  },
  {
    scope: "irn:read",
    label: "Rhythm notifications",
    detail: "Explicit access to irregular-rhythm alerts",
    group: "Sensitive data",
  },
  {
    scope: "sync:write",
    label: "Trigger sync",
    detail: "Queue Google Health synchronization",
    group: "Actions",
  },
  {
    scope: "integration:write",
    label: "Manage connection",
    detail: "Start or disconnect Google Health authorization",
    group: "Actions",
  },
];

const defaultScopes = new Set<AgentScope>([
  "profile:read",
  "today:read",
  "fitness:read",
  "sleep:read",
  "health:read",
  "nutrition:read",
  "sync:read",
  "integration:read",
]);

const scopeGroups: ScopeOption["group"][] = ["Read access", "Sensitive data", "Actions"];

function status(token: McpToken): string {
  if (token.revoked_at) return "Revoked";
  if (token.expires_at && new Date(token.expires_at) <= new Date()) return "Expired";
  return "Active";
}

function dateTime(value: string | null): string {
  return value
    ? new Date(value).toLocaleString([], { dateStyle: "medium", timeStyle: "short" })
    : "Never";
}

export function AgentAccess() {
  const client = useQueryClient();
  const [selectedScopes, setSelectedScopes] = useState<Set<AgentScope>>(
    () => new Set(defaultScopes),
  );
  const [issued, setIssued] = useState<IssuedMcpToken>();
  const [copiedToken, setCopiedToken] = useState(false);
  const [copiedUrl, setCopiedUrl] = useState(false);
  const [copyError, setCopyError] = useState<string>();
  const tokens = useQuery({
    queryKey: ["mcp-tokens"],
    queryFn: () => api<McpToken[]>("/mcp-tokens"),
  });
  const createToken = useMutation({
    mutationFn: (payload: { name: string; scopes: AgentScope[]; expires_at?: string }) =>
      api<IssuedMcpToken>("/mcp-tokens", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: (token) => {
      setIssued(token);
      setCopiedToken(false);
      setCopiedUrl(false);
      setCopyError(undefined);
      void client.invalidateQueries({ queryKey: ["mcp-tokens"] });
    },
  });
  const revokeToken = useMutation({
    mutationFn: (id: string) => api<void>(`/mcp-tokens/${id}`, { method: "DELETE" }),
    onSuccess: () => void client.invalidateQueries({ queryKey: ["mcp-tokens"] }),
  });

  function toggleScope(scope: AgentScope) {
    setSelectedScopes((current) => {
      const next = new Set(current);
      if (next.has(scope)) next.delete(scope);
      else next.add(scope);
      return next;
    });
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const name = String(form.get("name") ?? "").trim();
    const expires = String(form.get("expires") ?? "");
    createToken.mutate({
      name,
      scopes: [...selectedScopes],
      ...(expires ? { expires_at: new Date(`${expires}T23:59:59`).toISOString() } : {}),
    });
  }

  async function copySecret(value: string, kind: "token" | "url") {
    try {
      await navigator.clipboard.writeText(value);
      setCopiedToken(kind === "token");
      setCopiedUrl(kind === "url");
      setCopyError(undefined);
    } catch {
      setCopyError("Clipboard unavailable. Select and copy the token manually.");
    }
  }

  function copyToken() {
    if (issued) void copySecret(issued.token, "token");
  }

  function copyMcpUrl() {
    if (!issued) return;
    void copySecret(issued.mcp_url, "url");
  }

  return (
    <div className="grid gap-6">
      {issued && (
        <Card variant="default" aria-labelledby="new-token-title">
          <Card.Header>
            <SectionHeader
              action={
                <Chip color="success" size="sm" variant="soft">
                  <Chip.Label>Created successfully</Chip.Label>
                </Chip>
              }
              eyebrow="New credential"
              id="new-token-title"
              title="Copy this token now"
            />
          </Card.Header>
          <Card.Content className="grid gap-3">
            <Typography.Paragraph color="muted" size="sm">
              LifeStats stores only its hash. This value cannot be shown again.
            </Typography.Paragraph>
            <Typography.Code className="block overflow-x-auto rounded-lg bg-surface-tertiary p-3">
              {issued.token}
            </Typography.Code>
            <Typography.Code className="block overflow-x-auto rounded-lg bg-surface-tertiary p-3">
              {issued.mcp_url}
            </Typography.Code>
            {copyError && <AppAlert message={copyError} title="Clipboard unavailable" />}
          </Card.Content>
          <Card.Footer className="flex flex-wrap gap-2">
            <AppButton onPress={copyMcpUrl} type="button">
              {copiedUrl ? "URL copied" : "Copy MCP URL"}
            </AppButton>
            <AppButton onPress={copyToken} tone="secondary" type="button">
              {copiedToken ? "Token copied" : "Copy token"}
            </AppButton>
            <AppButton onPress={() => setIssued(undefined)} tone="secondary" type="button">
              I saved it
            </AppButton>
          </Card.Footer>
        </Card>
      )}

      <div className="grid grid-cols-[minmax(0,1.05fr)_minmax(360px,0.95fr)] items-start gap-4 max-xl:grid-cols-1">
        <Card variant="secondary" aria-labelledby="create-token-title">
          <Card.Header>
            <SectionHeader
              eyebrow="New credential"
              id="create-token-title"
              title="Create MCP token"
            />
          </Card.Header>
          <Card.Content>
            <form className="grid gap-5" onSubmit={submit}>
              <div className="grid grid-cols-2 gap-3 max-sm:grid-cols-1">
                <AppTextField
                  defaultValue="Codex"
                  inputProps={{
                    autoComplete: "off",
                    maxLength: 100,
                  }}
                  isRequired
                  label="Name"
                  name="name"
                />
                <AppTextField
                  description="Optional"
                  inputProps={{
                    min: new Date().toISOString().slice(0, 10),
                    type: "date",
                  }}
                  label="Expires"
                  name="expires"
                />
              </div>

              <div className="grid gap-5">
                {scopeGroups.map((group) => (
                  <fieldset
                    className="grid grid-cols-2 gap-x-4 border-t border-separator pt-3 max-sm:grid-cols-1"
                    key={group}
                  >
                    <legend className="pr-2 text-xs font-semibold text-muted">{group}</legend>
                    {scopeOptions
                      .filter((option) => option.group === group)
                      .map((option) => (
                        <Checkbox
                          isSelected={selectedScopes.has(option.scope)}
                          key={option.scope}
                          name="scopes"
                          onChange={() => toggleScope(option.scope)}
                          value={option.scope}
                          variant="secondary"
                        >
                          <Checkbox.Content className="items-start py-2.5">
                            <Checkbox.Control>
                              <Checkbox.Indicator />
                            </Checkbox.Control>
                            <span className="min-w-0">
                              <span className="block text-sm font-semibold">
                                {option.label}
                              </span>
                              <span className="block text-xs text-muted">
                                {option.detail}
                              </span>
                            </span>
                          </Checkbox.Content>
                        </Checkbox>
                      ))}
                  </fieldset>
                ))}
              </div>

              {createToken.error && (
                <AppAlert message={createToken.error.message} title="Token creation failed" />
              )}
              <AppButton
                className="justify-self-start"
                isDisabled={createToken.isPending || selectedScopes.size === 0}
                isPending={createToken.isPending}
                type="submit"
              >
                {createToken.isPending ? "Creating…" : "Create token"}
              </AppButton>
            </form>
          </Card.Content>
        </Card>

        <Card variant="secondary" aria-labelledby="tokens-title">
          <Card.Header>
            <SectionHeader
              action={
                tokens.data ? (
                  <Chip size="sm" variant="soft">
                    <Chip.Label>{tokens.data.length}</Chip.Label>
                  </Chip>
                ) : undefined
              }
              eyebrow="Credentials"
              id="tokens-title"
              title="MCP tokens"
            />
          </Card.Header>
          <Card.Content className="grid gap-3">
            {tokens.isPending && (
              <div className="grid justify-items-center gap-2 py-10" role="status">
                <Spinner color="accent" />
                <Typography color="muted" type="body-sm">
                  Loading tokens…
                </Typography>
              </div>
            )}
            {tokens.isError && (
              <AppAlert message={tokens.error.message} title="Tokens unavailable" />
            )}
            {tokens.data?.length === 0 && (
              <EmptyContent
                description="Create one when connecting an MCP client."
                icon={<KeyRound className="size-6" />}
                title="No MCP tokens"
              />
            )}
            {tokens.data && tokens.data.length > 0 && (
              <ul className="grid gap-3">
                {tokens.data.map((token) => {
                  const tokenStatus = status(token);
                  return (
                    <Surface className="grid gap-3 p-4" key={token.id} variant="tertiary">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <Typography className="block" truncate weight="semibold">
                            {token.name}
                          </Typography>
                          <Typography.Code>{token.token_prefix}…</Typography.Code>
                        </div>
                        <Chip
                          color={tokenStatus === "Active" ? "success" : "danger"}
                          size="sm"
                          variant="soft"
                        >
                          <Chip.Label>{tokenStatus}</Chip.Label>
                        </Chip>
                      </div>
                      <dl className="grid grid-cols-3 gap-3 max-sm:grid-cols-1">
                        {[
                          ["Created", dateTime(token.created_at)],
                          ["Last used", dateTime(token.last_used_at)],
                          [
                            "Expires",
                            token.expires_at ? dateTime(token.expires_at) : "No expiry",
                          ],
                        ].map(([label, value]) => (
                          <div key={label}>
                            <dt className="text-xs text-muted">{label}</dt>
                            <dd className="mt-1 text-xs tabular-nums">{value}</dd>
                          </div>
                        ))}
                      </dl>
                      <Typography.Code className="break-words text-xs text-muted">
                        {token.scopes.join(" · ")}
                      </Typography.Code>
                      {!token.revoked_at && (
                        <AppButton
                          className="justify-self-start"
                          isDisabled={revokeToken.isPending}
                          onPress={() => {
                            if (
                              window.confirm(
                                `Revoke “${token.name}”? The MCP client will lose access.`,
                              )
                            ) {
                              revokeToken.mutate(token.id);
                            }
                          }}
                          tone="danger"
                          type="button"
                        >
                          Revoke
                        </AppButton>
                      )}
                    </Surface>
                  );
                })}
              </ul>
            )}
            {revokeToken.error && (
              <AppAlert message={revokeToken.error.message} title="Token revocation failed" />
            )}
          </Card.Content>
        </Card>
      </div>
    </div>
  );
}
