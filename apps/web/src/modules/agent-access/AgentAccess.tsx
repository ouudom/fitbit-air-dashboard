"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { AgentOAuthGrant } from "@/lib/types";

function dateTime(value: string | null): string {
  return value
    ? new Date(value).toLocaleString([], { dateStyle: "medium", timeStyle: "short" })
    : "Never";
}

export function AgentAccess() {
  const queryClient = useQueryClient();
  const grants = useQuery({
    queryKey: ["oauth-grants"],
    queryFn: () => api<AgentOAuthGrant[]>("/oauth-grants"),
  });
  const revokeGrant = useMutation({
    mutationFn: (id: string) => api<void>(`/oauth-grants/${id}`, { method: "DELETE" }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["oauth-grants"] }),
  });

  return (
    <div className="viewStack agentAccessView">
      <header className="pageHeader">
        <div>
          <p className="eyebrow">Account utility</p>
          <h1>Agent access</h1>
          <p>Connect an MCP client with browser sign-in. No token or client secret to copy.</p>
        </div>
      </header>

      <div className="agentAccessGrid">
        <section className="panel tokenCreatePanel" aria-labelledby="connect-agent-title">
          <div className="panelHeading">
            <div>
              <p className="sectionKicker">OAuth 2.1 + PKCE</p>
              <h2 id="connect-agent-title">Connect an agent</h2>
            </div>
          </div>

          <div className="agentSetup">
            <p>
              Use your LifeStats MCP URL. Your agent registers itself, opens this app, and asks
              which permissions to grant.
            </p>

            <div>
              <strong>Hermes</strong>
              <pre>
                <code>{`mcp_servers:
  lifestats:
    url: https://your-host.example/mcp
    auth: oauth`}</code>
              </pre>
            </div>

            <div>
              <strong>Codex</strong>
              <pre>
                <code>{`[mcp_servers.lifestats]
url = "https://your-host.example/mcp"
auth = "oauth"`}</code>
              </pre>
              <p>
                Then run <code>codex mcp login lifestats</code>.
              </p>
            </div>

            <div>
              <strong>Claude Code</strong>
              <pre>
                <code>{`claude mcp add --transport http lifestats \\
  https://your-host.example/mcp`}</code>
              </pre>
              <p>Open <code>/mcp</code> and authenticate.</p>
            </div>
          </div>
        </section>

        <section className="panel tokenListPanel" aria-labelledby="connections-title">
          <div className="panelHeading">
            <div>
              <p className="sectionKicker">Your account</p>
              <h2 id="connections-title">Connected agents</h2>
            </div>
            {grants.data && <span className="countPill">{grants.data.length}</span>}
          </div>

          {grants.isPending && <p className="tokenListState">Loading connections…</p>}
          {grants.isError && (
            <p className="errorBanner" role="alert">
              {grants.error.message}
            </p>
          )}
          {grants.data?.length === 0 && (
            <div className="emptyState compactEmpty">
              <span aria-hidden="true">⌘</span>
              <strong>No connected agents</strong>
              <p>Start OAuth from Hermes, Codex, or Claude.</p>
            </div>
          )}
          {grants.data && grants.data.length > 0 && (
            <ul className="tokenList">
              {grants.data.map((grant) => (
                <li key={grant.id}>
                  <div className="tokenIdentity">
                    <strong>{grant.client_name}</strong>
                    <code>{grant.client_id}</code>
                  </div>
                  <span className={`tokenStatus ${grant.revoked_at ? "revoked" : "active"}`}>
                    {grant.revoked_at ? "Revoked" : "Active"}
                  </span>
                  <dl>
                    <div>
                      <dt>Connected</dt>
                      <dd>{dateTime(grant.created_at)}</dd>
                    </div>
                    <div>
                      <dt>Last used</dt>
                      <dd>{dateTime(grant.last_used_at)}</dd>
                    </div>
                    <div>
                      <dt>Resource</dt>
                      <dd>{grant.resource}</dd>
                    </div>
                  </dl>
                  <p className="tokenScopes">{grant.scopes.join(" · ")}</p>
                  {!grant.revoked_at && (
                    <button
                      className="dangerButton"
                      disabled={revokeGrant.isPending}
                      onClick={() => {
                        if (
                          window.confirm(
                            `Disconnect “${grant.client_name}”? Its tokens stop working.`,
                          )
                        ) {
                          revokeGrant.mutate(grant.id);
                        }
                      }}
                      type="button"
                    >
                      Disconnect
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}
          {revokeGrant.error && (
            <p className="errorBanner" role="alert">
              {revokeGrant.error.message}
            </p>
          )}
        </section>
      </div>
    </div>
  );
}
