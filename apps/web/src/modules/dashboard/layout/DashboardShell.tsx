import type { ReactNode } from "react";

export type DashboardView = "overview" | "sleep";

type DashboardShellProps = {
  activeView: DashboardView;
  children: ReactNode;
  email: string;
  logoutPending: boolean;
  onLogout: () => void;
  onNavigate: (view: DashboardView) => void;
  syncLabel: string;
};

const navigation: Array<{ id: DashboardView; label: string; shortLabel: string; icon: string }> = [
  { id: "overview", label: "Batcave Overview", shortLabel: "Overview", icon: "⌂" },
  { id: "sleep", label: "Stasis Architecture", shortLabel: "Stasis", icon: "☾" },
];

export function DashboardShell({
  activeView,
  children,
  email,
  logoutPending,
  onLogout,
  onNavigate,
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
          <p>Health views</p>
          {navigation.map((item) => (
            <button
              aria-current={activeView === item.id ? "page" : undefined}
              className={activeView === item.id ? "active" : undefined}
              key={item.id}
              onClick={() => onNavigate(item.id)}
            >
              <span aria-hidden="true">{item.icon}</span>
              {item.label}
            </button>
          ))}
        </nav>

        <div className="accountBlock">
          <span className="avatar" aria-hidden="true">
            {email.charAt(0).toUpperCase()}
          </span>
          <div>
            <strong>Private account</strong>
            <small title={email}>{email}</small>
          </div>
          <button className="signOutButton" disabled={logoutPending} onClick={onLogout}>
            {logoutPending ? "Signing out…" : "Sign out"}
          </button>
        </div>
      </aside>

      <header className="mobileHeader">
        <span className="brandMark" aria-hidden="true">
          LS
        </span>
        <strong>LIFESTATS</strong>
        <span className="mobileSync">{syncLabel}</span>
      </header>

      <main className="dashboardMain">{children}</main>

      <nav className="mobileNavigation" aria-label="Primary">
        {navigation.map((item) => (
          <button
            aria-current={activeView === item.id ? "page" : undefined}
            className={activeView === item.id ? "active" : undefined}
            key={item.id}
            onClick={() => onNavigate(item.id)}
          >
            <span aria-hidden="true">{item.icon}</span>
            {item.shortLabel}
          </button>
        ))}
      </nav>
    </div>
  );
}
