"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
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
    label: "Today",
    detail: "Daily metrics and timeline",
    group: "Read access",
  },
  {
    scope: "fitness:read",
    label: "Fitness",
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
    <div className="viewStack agentAccessView">
      <header className="pageHeader">
        <div>
          <p className="eyebrow">Account utility</p>
          <h1>Agent access</h1>
          <p>Create scoped credentials for any Streamable HTTP MCP client.</p>
        </div>
      </header>

      {issued && (
        <section className="secretPanel" aria-labelledby="new-token-title">
          <div>
            <p className="sectionKicker">Created successfully</p>
            <h2 id="new-token-title">Copy this token now</h2>
            <p>LifeStats stores only its hash. This value cannot be shown again.</p>
          </div>
          <code>{issued.token}</code>
          <code>{issued.mcp_url}</code>
          {copyError && (
            <p className="errorBanner" role="alert">
              {copyError}
            </p>
          )}
          <div className="tokenActions">
            <button className="primaryButton" onClick={copyMcpUrl} type="button">
              {copiedUrl ? "URL copied" : "Copy MCP URL"}
            </button>
            <button className="secondaryButton" onClick={copyToken} type="button">
              {copiedToken ? "Token copied" : "Copy token"}
            </button>
            <button className="secondaryButton" onClick={() => setIssued(undefined)} type="button">
              I saved it
            </button>
          </div>
        </section>
      )}

      <div className="agentAccessGrid">
        <section className="panel tokenCreatePanel" aria-labelledby="create-token-title">
          <div className="panelHeading">
            <div>
              <p className="sectionKicker">New credential</p>
              <h2 id="create-token-title">Create MCP token</h2>
            </div>
          </div>

          <form className="tokenForm" onSubmit={submit}>
            <div className="tokenFormFields">
              <label>
                <span>Name</span>
                <input
                  autoComplete="off"
                  defaultValue="Codex"
                  maxLength={100}
                  name="name"
                  required
                />
              </label>
              <label>
                <span>Expires</span>
                <input min={new Date().toISOString().slice(0, 10)} name="expires" type="date" />
                <small>Optional</small>
              </label>
            </div>

            <div className="scopeGroups">
              {scopeGroups.map((group) => (
                <fieldset key={group}>
                  <legend>{group}</legend>
                  {scopeOptions
                    .filter((option) => option.group === group)
                    .map((option) => (
                      <label className="scopeOption" key={option.scope}>
                        <input
                          checked={selectedScopes.has(option.scope)}
                          onChange={() => toggleScope(option.scope)}
                          type="checkbox"
                        />
                        <span>
                          <strong>{option.label}</strong>
                          <small>{option.detail}</small>
                        </span>
                      </label>
                    ))}
                </fieldset>
              ))}
            </div>

            {createToken.error && (
              <p className="errorBanner" role="alert">
                {createToken.error.message}
              </p>
            )}
            <button
              className="primaryButton"
              disabled={createToken.isPending || selectedScopes.size === 0}
              type="submit"
            >
              {createToken.isPending ? "Creating…" : "Create token"}
            </button>
          </form>
        </section>

        <section className="panel tokenListPanel" aria-labelledby="tokens-title">
          <div className="panelHeading">
            <div>
              <p className="sectionKicker">Credentials</p>
              <h2 id="tokens-title">MCP tokens</h2>
            </div>
            {tokens.data && <span className="countPill">{tokens.data.length}</span>}
          </div>

          {tokens.isPending && <p className="tokenListState">Loading tokens…</p>}
          {tokens.isError && (
            <p className="errorBanner" role="alert">
              {tokens.error.message}
            </p>
          )}
          {tokens.data?.length === 0 && (
            <div className="emptyState compactEmpty">
              <span aria-hidden="true">⌘</span>
              <strong>No MCP tokens</strong>
              <p>Create one when connecting an MCP client.</p>
            </div>
          )}
          {tokens.data && tokens.data.length > 0 && (
            <ul className="tokenList">
              {tokens.data.map((token) => {
                const tokenStatus = status(token);
                return (
                  <li key={token.id}>
                    <div className="tokenIdentity">
                      <strong>{token.name}</strong>
                      <code>{token.token_prefix}…</code>
                    </div>
                    <span className={`tokenStatus ${tokenStatus.toLowerCase()}`}>
                      {tokenStatus}
                    </span>
                    <dl>
                      <div>
                        <dt>Created</dt>
                        <dd>{dateTime(token.created_at)}</dd>
                      </div>
                      <div>
                        <dt>Last used</dt>
                        <dd>{dateTime(token.last_used_at)}</dd>
                      </div>
                      <div>
                        <dt>Expires</dt>
                        <dd>{token.expires_at ? dateTime(token.expires_at) : "No expiry"}</dd>
                      </div>
                    </dl>
                    <p className="tokenScopes">{token.scopes.join(" · ")}</p>
                    {!token.revoked_at && (
                      <button
                        className="dangerButton"
                        disabled={revokeToken.isPending}
                        onClick={() => {
                          if (
                            window.confirm(
                              `Revoke “${token.name}”? The MCP client will lose access.`,
                            )
                          ) {
                            revokeToken.mutate(token.id);
                          }
                        }}
                        type="button"
                      >
                        Revoke
                      </button>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
          {revokeToken.error && (
            <p className="errorBanner" role="alert">
              {revokeToken.error.message}
            </p>
          )}
        </section>
      </div>
    </div>
  );
}
