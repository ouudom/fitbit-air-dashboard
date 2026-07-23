"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { ApiError, api } from "@/lib/api";
import type {
  OAuthAuthorizationDecision,
  OAuthAuthorizationPreview,
  OAuthAuthorizationResult,
  Session,
} from "@/lib/types";
import { AuthScreen } from "@/modules/auth/AuthScreen";

const scopeLabels: Record<string, string> = {
  "profile:read": "Read profile and timezone",
  "today:read": "Read today metrics and timeline",
  "fitness:read": "Read activity, exercise, and trends",
  "sleep:read": "Read sleep sessions and trends",
  "health:read": "Read health measurements",
  "nutrition:read": "Read nutrition and hydration",
  "sync:read": "Read synchronization status",
  "sync:write": "Trigger Google Health synchronization",
  "integration:read": "Read Google Health connection status",
  "integration:write": "Manage Google Health connection",
  "ecg:read": "Read electrocardiogram records",
  "irn:read": "Read irregular-rhythm notifications",
};

function authorizationPayload(params: URLSearchParams): OAuthAuthorizationDecision {
  return {
    approved: true,
    client_id: params.get("client_id") ?? "",
    redirect_uri: params.get("redirect_uri") ?? "",
    response_type: "code",
    code_challenge: params.get("code_challenge") ?? "",
    code_challenge_method: "S256",
    scope: params.get("scope") ?? "",
    resource: params.get("resource") ?? "",
    state: params.get("state"),
  };
}

export function OAuthConsent() {
  const searchParams = useSearchParams();
  const query = searchParams.toString();
  const session = useQuery({
    queryKey: ["session"],
    queryFn: () => api<Session>("/session"),
  });
  const preview = useQuery({
    queryKey: ["oauth-authorization-preview", query],
    queryFn: () =>
      api<OAuthAuthorizationPreview>(`/oauth/authorize/preview?${query}`),
    enabled: session.isSuccess,
  });
  const decision = useMutation({
    mutationFn: (approved: boolean) =>
      api<OAuthAuthorizationResult>("/oauth/authorize/decision", {
        method: "POST",
        body: JSON.stringify({ ...authorizationPayload(searchParams), approved }),
      }),
    onSuccess: ({ redirect_to }) => window.location.assign(redirect_to),
  });

  if (session.isPending) {
    return (
      <main className="center">
        <div className="loader" role="status">
          Checking session…
        </div>
      </main>
    );
  }
  if (session.error instanceof ApiError && session.error.status === 401) return <AuthScreen />;
  if (session.isError) {
    return (
      <main className="center">
        <p className="errorBanner" role="alert">
          {session.error.message}
        </p>
      </main>
    );
  }

  return (
    <main className="oauthConsentPage">
      <section className="oauthConsentPanel" aria-labelledby="oauth-consent-title">
        <p className="eyebrow">Agent authorization</p>
        {preview.isPending && <div className="loader">Checking request…</div>}
        {preview.isError && (
          <>
            <h1 id="oauth-consent-title">Invalid authorization request</h1>
            <p className="errorBanner" role="alert">
              {preview.error.message}
            </p>
          </>
        )}
        {preview.data && (
          <>
            <h1 id="oauth-consent-title">Connect {preview.data.client_name}?</h1>
            <p>
              Unverified, dynamically registered client. Confirm its callback before sharing
              private LifeStats data.
            </p>

            <div className="consentResource">
              <span>Connecting to</span>
              <code>{preview.data.resource}</code>
            </div>
            <div className="consentResource">
              <span>Returns authorization to</span>
              <code>{preview.data.redirect_uri}</code>
            </div>

            <h2>Requested permissions</h2>
            <ul className="consentScopes">
              {preview.data.scopes.map((scope) => (
                <li key={scope}>{scopeLabels[scope] ?? scope}</li>
              ))}
            </ul>

            {decision.error && (
              <p className="errorBanner" role="alert">
                {decision.error.message}
              </p>
            )}
            <div className="consentActions">
              <button
                className="secondaryButton"
                disabled={decision.isPending}
                onClick={() => decision.mutate(false)}
                type="button"
              >
                Deny
              </button>
              <button
                className="primaryButton"
                disabled={decision.isPending}
                onClick={() => decision.mutate(true)}
                type="button"
              >
                {decision.isPending ? "Connecting…" : "Allow access"}
              </button>
            </div>
          </>
        )}
      </section>
    </main>
  );
}
