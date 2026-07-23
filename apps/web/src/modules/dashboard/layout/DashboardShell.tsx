import Link from "next/link";
import type { ReactNode } from "react";

export type DashboardView = "overview" | "sleep" | "agents";

type DashboardShellProps = {
  activeView: DashboardView;
  children: ReactNode;
  email: string;
  logoutPending: boolean;
  onLogout: () => void;
  syncLabel: string;
};

const navigation: Array<{
  id: DashboardView;
  href: string;
  label: string;
  shortLabel: string;
  icon: string;
}> = [
  { id: "overview", href: "/dashboard", label: "Today", shortLabel: "Today", icon: "⌂" },
  { id: "sleep", href: "/sleep", label: "Sleep", shortLabel: "Sleep", icon: "☾" },
];

export function DashboardShell({
  activeView,
  children,
  email,
  logoutPending,
  onLogout,
  syncLabel,
}: DashboardShellProps) {
  return (
    <div className="dashboardShell">
      <aside className="sideRail">
        <div className="brandBlock">
          <span className="brandMark" aria-hidden="true">
            LS
          </span>
          <div>
            <strong>LIFESTATS</strong>
            <small>Google Health companion</small>
          </div>
        </div>

        <div className="railStatus" aria-label={`Google Health status: ${syncLabel}`}>
          <span>Google Health</span>
          <strong>
            <i aria-hidden="true" />
            {syncLabel}
          </strong>
        </div>

        <nav className="railNavigation" aria-label="Primary">
          {navigation.map((item) => (
            <Link
              aria-current={activeView === item.id ? "page" : undefined}
              className={activeView === item.id ? "active" : undefined}
              href={item.href}
              key={item.id}
            >
              <span aria-hidden="true">{item.icon}</span>
              {item.label}
            </Link>
          ))}
        </nav>

        <Link
          aria-current={activeView === "agents" ? "page" : undefined}
          className={activeView === "agents" ? "agentAccessLink active" : "agentAccessLink"}
          href="/settings/agent-access"
        >
          <span aria-hidden="true">⌘</span>
          Agent access
        </Link>

        <footer className="sidebarFooter">
          <span className="avatar" aria-hidden="true">
            {email.charAt(0).toUpperCase()}
          </span>
          <div className="accountIdentity">
            <strong title={email}>{email}</strong>
            <small>Private account</small>
          </div>
          <button className="signOutButton" disabled={logoutPending} onClick={onLogout}>
            {logoutPending ? "Wait…" : "Sign out"}
          </button>
        </footer>
      </aside>

      <header className="mobileHeader">
        <span className="brandMark" aria-hidden="true">
          LS
        </span>
        <strong>LIFESTATS</strong>
        <div className="mobileUtilities">
          <span className="mobileSync">{syncLabel}</span>
          <Link aria-label="Agent access" href="/settings/agent-access">
            ⌘
          </Link>
        </div>
      </header>

      <main className="dashboardMain">{children}</main>

      <nav className="mobileNavigation" aria-label="Primary">
        {navigation.map((item) => (
          <Link
            aria-current={activeView === item.id ? "page" : undefined}
            className={activeView === item.id ? "active" : undefined}
            href={item.href}
            key={item.id}
          >
            <span aria-hidden="true">{item.icon}</span>
            {item.shortLabel}
          </Link>
        ))}
      </nav>
    </div>
  );
}
