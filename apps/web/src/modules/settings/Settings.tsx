"use client";

import { buttonVariants, Card, Chip, Spinner, Surface, Typography } from "@heroui/react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AppAlert } from "@/components/ui/AppAlert";
import { AppButton } from "@/components/ui/AppButton";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { api } from "@/lib/api";
import type { Dashboard } from "@/lib/types";
import { AgentAccess } from "@/modules/agent-access/AgentAccess";

type IntegrationStatus = {
  connected: boolean;
  status: string;
  grantedScopes: string[];
  enabledDataTypes: number;
  totalDataTypes: number;
  lastVerifiedAt?: string | null;
  tokenExpiresAt?: string | null;
};

type SettingsProps = {
  dashboard: Dashboard;
  email: string;
  integration?: IntegrationStatus;
  integrationError?: string;
  integrationLoading: boolean;
  onSync: () => void;
  syncError?: string;
  syncing: boolean;
};

function dateTime(value?: string | null): string {
  return value
    ? new Date(value).toLocaleString([], { dateStyle: "medium", timeStyle: "short" })
    : "Never";
}

function statusColor(status?: string): "success" | "danger" | "warning" {
  if (status === "active") return "success";
  if (status === "disconnected" || status === "revoked") return "danger";
  return "warning";
}

export function Settings({
  dashboard,
  email,
  integration,
  integrationError,
  integrationLoading,
  onSync,
  syncError,
  syncing,
}: SettingsProps) {
  const client = useQueryClient();
  const disconnect = useMutation({
    mutationFn: () =>
      api<{ status: string; cacheRetained: boolean }>(
        "/integrations/google-health/disconnect",
        { method: "POST" },
      ),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["google-health-integration"] });
      void client.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
  const syncRecords = dashboard.sync.reduce((sum, item) => sum + item.recordCount, 0);
  const lastSync = dashboard.sync
    .map((item) => item.lastSyncedAt)
    .filter((value): value is string => Boolean(value))
    .sort()
    .at(-1);
  const failedJobs = dashboard.sync.filter((item) => item.status === "failed");

  return (
    <div className="mx-auto grid w-full max-w-6xl gap-8">
      <PageHeader
        description="Manage account, Google Health synchronization, and agent credentials."
        eyebrow="Private account"
        title="Settings"
      />

      <nav className="flex flex-wrap gap-2" aria-label="Settings sections">
        {[
          ["Account", "#account"],
          ["Google Health Sync Status", "#google-health-sync"],
          ["Agent access", "#agent-access"],
        ].map(([label, href]) => (
          <a className={buttonVariants({ variant: "secondary" })} href={href} key={href}>
            {label}
          </a>
        ))}
      </nav>

      <section className="scroll-mt-24" id="account" aria-labelledby="account-title">
        <Card variant="secondary">
          <Card.Header>
            <SectionHeader eyebrow="Profile" id="account-title" title="Account" />
          </Card.Header>
          <Card.Content>
            <dl className="grid grid-cols-2 gap-4 max-sm:grid-cols-1">
              <Surface className="p-4" variant="tertiary">
                <dt className="text-xs text-muted">Email</dt>
                <dd className="mt-1 break-words text-sm font-semibold">{email}</dd>
              </Surface>
              <Surface className="p-4" variant="tertiary">
                <dt className="text-xs text-muted">Timezone</dt>
                <dd className="mt-1 text-sm font-semibold">{dashboard.timezone}</dd>
              </Surface>
            </dl>
          </Card.Content>
        </Card>
      </section>

      <section
        className="scroll-mt-24"
        id="google-health-sync"
        aria-labelledby="google-health-sync-title"
      >
        <Card variant="secondary">
          <Card.Header>
            <SectionHeader
              action={
                integration && (
                  <Chip color={statusColor(integration.status)} size="sm" variant="soft">
                    <Chip.Label>{integration.status.replaceAll("-", " ")}</Chip.Label>
                  </Chip>
                )
              }
              eyebrow="Authoritative source"
              id="google-health-sync-title"
              title="Google Health Sync Status"
            />
          </Card.Header>
          <Card.Content className="grid gap-4">
            {integrationLoading && (
              <div className="flex items-center gap-3 py-3" role="status">
                <Spinner color="accent" size="sm" />
                <Typography color="muted" type="body-sm">
                  Checking Google Health…
                </Typography>
              </div>
            )}
            {integrationError && (
              <AppAlert message={integrationError} title="Connection status unavailable" />
            )}
            {integration && (
              <>
                <dl className="grid grid-cols-4 gap-3 max-xl:grid-cols-2 max-sm:grid-cols-1">
                  {[
                    ["Connection", integration.connected ? "Connected" : "Not connected"],
                    [
                      "Data types",
                      `${integration.enabledDataTypes} of ${integration.totalDataTypes} enabled`,
                    ],
                    ["Last successful sync", dateTime(lastSync)],
                    ["Synced records", syncRecords.toLocaleString()],
                  ].map(([label, value]) => (
                    <Surface className="p-4" key={label} variant="tertiary">
                      <dt className="text-xs text-muted">{label}</dt>
                      <dd className="mt-1 text-sm font-semibold">{value}</dd>
                    </Surface>
                  ))}
                </dl>

                {failedJobs.length > 0 && (
                  <AppAlert
                    message={`${failedJobs.length} data type${failedJobs.length === 1 ? "" : "s"} failed during the latest sync.`}
                    title="Sync needs attention"
                  />
                )}
                {syncError && <AppAlert message={syncError} title="Sync failed" />}
                {disconnect.error && (
                  <AppAlert message={disconnect.error.message} title="Disconnect failed" />
                )}

                <div className="flex flex-wrap gap-2">
                  {!integration.connected ? (
                    <a
                      className={buttonVariants({ variant: "primary" })}
                      href="/api/v1/integrations/google-health/connect"
                    >
                      Connect Google Health
                    </a>
                  ) : (
                    <>
                      <AppButton isDisabled={syncing} isPending={syncing} onPress={onSync}>
                        {syncing ? "Syncing…" : "Sync now"}
                      </AppButton>
                      <AppButton
                        isDisabled={disconnect.isPending}
                        onPress={() => {
                          if (
                            window.confirm(
                              "Disconnect Google Health? Synced cache stays available.",
                            )
                          ) {
                            disconnect.mutate();
                          }
                        }}
                        tone="danger"
                      >
                        {disconnect.isPending ? "Disconnecting…" : "Disconnect"}
                      </AppButton>
                    </>
                  )}
                </div>
              </>
            )}
          </Card.Content>
        </Card>
      </section>

      <section className="scroll-mt-24" id="agent-access" aria-labelledby="agent-access-title">
        <div className="mb-4">
          <SectionHeader
            eyebrow="MCP credentials"
            id="agent-access-title"
            title="Agent access"
          />
          <Typography.Paragraph className="mt-1" color="muted" size="sm">
            Create scoped credentials for Streamable HTTP MCP clients.
          </Typography.Paragraph>
        </div>
        <AgentAccess />
      </section>
    </div>
  );
}
