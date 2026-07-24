"use client";

import {
  Avatar,
  buttonVariants,
  Card,
  Chip,
  Separator,
  Spinner,
  Typography,
} from "@heroui/react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
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
  logoutError?: string;
  logoutPending: boolean;
  onLogout: () => void;
  onSync: () => void;
  syncError?: string;
  syncing: boolean;
};

type SettingsSection = "account" | "google-health-sync" | "agent-access";

const settingsSections: Array<{
  id: SettingsSection;
  label: string;
  detail: string;
}> = [
  { id: "account", label: "Account", detail: "Profile and session" },
  {
    id: "google-health-sync",
    label: "Google Health",
    detail: "Connection and sync",
  },
  { id: "agent-access", label: "Agent access", detail: "MCP credentials" },
];

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
  logoutError,
  logoutPending,
  onLogout,
  onSync,
  syncError,
  syncing,
}: SettingsProps) {
  const client = useQueryClient();
  const agentAccessEnabled = dashboard.capabilities.agentAccessEnabled;
  const visibleSettingsSections = agentAccessEnabled
    ? settingsSections
    : settingsSections.filter((section) => section.id !== "agent-access");
  const [activeSection, setActiveSection] = useState<SettingsSection>("account");

  useEffect(() => {
    function selectHashSection() {
      const section = window.location.hash.slice(1);
      if (section === "agent-access" && !agentAccessEnabled) {
        setActiveSection("account");
        window.history.replaceState(null, "", "#account");
      } else if (settingsSections.some((item) => item.id === section)) {
        setActiveSection(section as SettingsSection);
      }
    }

    selectHashSection();
    window.addEventListener("hashchange", selectHashSection);
    return () => window.removeEventListener("hashchange", selectHashSection);
  }, [agentAccessEnabled]);

  function selectSection(section: SettingsSection) {
    setActiveSection(section);
    window.history.replaceState(null, "", `#${section}`);
  }

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
        description={
          agentAccessEnabled
            ? "Manage your account, connected health data, and agent credentials."
            : "Manage your account and connected health data."
        }
        eyebrow="LifeStats"
        title="Settings"
      />

      <div className="grid grid-cols-[12rem_minmax(0,1fr)] items-start gap-8 max-lg:grid-cols-1">
        <nav
          className="sticky top-8 grid gap-1 max-lg:static max-lg:flex max-lg:overflow-x-auto max-lg:pb-1"
          aria-label="Settings sections"
          role="tablist"
        >
          {visibleSettingsSections.map((section) => (
            <button
              aria-controls={`${section.id}-panel`}
              aria-selected={activeSection === section.id}
              className={`group min-h-11 rounded-xl px-3 py-2.5 text-left transition-colors max-lg:min-w-max ${
                activeSection === section.id
                  ? "bg-accent-soft text-accent-soft-foreground"
                  : "text-muted hover:bg-surface-tertiary hover:text-foreground"
              }`}
              id={`${section.id}-tab`}
              key={section.id}
              onClick={() => selectSection(section.id)}
              role="tab"
              type="button"
            >
              <span className="block text-sm font-semibold">{section.label}</span>
              <span className="mt-0.5 block text-xs opacity-75 max-lg:hidden">
                {section.detail}
              </span>
            </button>
          ))}
        </nav>

        <div className="grid min-w-0 gap-10">
          {activeSection === "account" && (
            <section aria-labelledby="account-tab" id="account-panel" role="tabpanel">
              <Card variant="secondary">
                <Card.Header>
                  <SectionHeader eyebrow="Profile" id="account-title" title="Account" />
                </Card.Header>
                <Card.Content className="grid gap-5">
                  <div className="flex items-center gap-4 max-sm:items-start">
                    <Avatar color="accent" size="lg">
                      <Avatar.Fallback>{email.charAt(0).toUpperCase()}</Avatar.Fallback>
                    </Avatar>
                    <div className="min-w-0">
                      <Typography weight="semibold">Private account</Typography>
                      <Typography className="block break-words" color="muted" type="body-sm">
                        {email}
                      </Typography>
                    </div>
                  </div>

                  <Separator />

                  <dl className="grid grid-cols-2 gap-x-8 gap-y-4 max-sm:grid-cols-1">
                    <div>
                      <dt className="text-xs text-muted">Email address</dt>
                      <dd className="mt-1 break-words text-sm font-semibold">{email}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-muted">Timezone</dt>
                      <dd className="mt-1 text-sm font-semibold">{dashboard.timezone}</dd>
                    </div>
                  </dl>

                  <Separator />

                  <div className="flex items-center justify-between gap-6 max-sm:items-start">
                    <div>
                      <Typography weight="semibold">Current session</Typography>
                      <Typography className="mt-1 block" color="muted" type="body-xs">
                        Sign out on this device.
                      </Typography>
                    </div>
                    <AppButton
                      isDisabled={logoutPending}
                      isPending={logoutPending}
                      onPress={onLogout}
                      tone="secondary"
                    >
                      {logoutPending ? "Signing out…" : "Sign out"}
                    </AppButton>
                  </div>
                  {logoutError && <AppAlert message={logoutError} title="Sign out failed" />}
                </Card.Content>
              </Card>
            </section>
          )}

          {activeSection === "google-health-sync" && (
            <section
              aria-labelledby="google-health-sync-tab"
              id="google-health-sync-panel"
              role="tabpanel"
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
                  title="Google Health"
                />
              </Card.Header>
              <Card.Content className="grid gap-5">
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
                    <div className="flex items-center justify-between gap-6 max-sm:items-start">
                      <div>
                        <Typography weight="semibold">
                          {integration.connected ? "Google Health connected" : "Not connected"}
                        </Typography>
                        <Typography className="mt-1 block" color="muted" type="body-xs">
                          {integration.connected
                            ? "Health data syncs into a local, rebuildable cache."
                            : "Connect Google Health to import supported health data."}
                        </Typography>
                      </div>
                      {!integration.connected && (
                        <a
                          className={buttonVariants({ variant: "primary" })}
                          href="/api/v1/integrations/google-health/connect"
                        >
                          Connect
                        </a>
                      )}
                    </div>

                    <Separator />

                    <dl className="grid grid-cols-3 gap-6 max-md:grid-cols-1">
                      {[
                        [
                          "Data types",
                          `${integration.enabledDataTypes} of ${integration.totalDataTypes} enabled`,
                        ],
                        ["Last successful sync", dateTime(lastSync)],
                        ["Synced records", syncRecords.toLocaleString()],
                      ].map(([label, value]) => (
                        <div key={label}>
                          <dt className="text-xs text-muted">{label}</dt>
                          <dd className="mt-1 text-sm font-semibold">{value}</dd>
                        </div>
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

                    {integration.connected && (
                      <>
                        <Separator />
                        <div className="flex flex-wrap gap-2">
                          <AppButton
                            isDisabled={syncing}
                            isPending={syncing}
                            onPress={onSync}
                          >
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
                        </div>
                      </>
                    )}
                  </>
                )}
              </Card.Content>
              </Card>
            </section>
          )}

          {agentAccessEnabled && activeSection === "agent-access" && (
            <section
              aria-labelledby="agent-access-tab"
              id="agent-access-panel"
              role="tabpanel"
            >
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
          )}
        </div>
      </div>
    </div>
  );
}
