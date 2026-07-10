import { NavLink } from "react-router-dom";
import {
  Activity,
  LayoutDashboard,
  Server,
  Bell,
  GitBranch,
  BarChart3,
  LogOut,
} from "lucide-react";
import { useAuthStore } from "../../store/auth";
import { cn } from "../../lib/utils";

const NAV_ITEMS = [
  { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/devices", label: "Devices", icon: Server },
  { to: "/alerts", label: "Alerts", icon: Bell },
  { to: "/incidents", label: "Incidents", icon: GitBranch },
  { to: "/models", label: "Model Comparison", icon: BarChart3 },
];

export function Sidebar() {
  const { user, logout } = useAuthStore();

  return (
    <aside className="hidden lg:flex w-60 shrink-0 flex-col border-r border-hairline bg-surface/60 backdrop-blur-sm">
      <div className="flex items-center gap-2.5 px-5 py-5">
        <div className="relative flex h-8 w-8 items-center justify-center rounded-lg bg-signal/10">
          <Activity size={18} className="text-signal" />
          <span className="absolute inset-0 rounded-lg border border-signal/30 animate-pulse-slow" />
        </div>
        <div>
          <div className="font-display text-base font-semibold leading-none">Pulse</div>
          <div className="text-[10px] text-dim leading-none mt-1 font-mono">AIOPS CONSOLE</div>
        </div>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-2">
        {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-signal/10 text-signal"
                  : "text-mute hover:bg-elevated hover:text-ink"
              )
            }
          >
            <Icon size={17} strokeWidth={2} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-hairline px-3 py-3">
        <div className="flex items-center justify-between rounded-lg px-3 py-2">
          <div className="min-w-0">
            <div className="truncate text-sm font-medium text-ink">{user?.username}</div>
            <div className="truncate text-xs text-dim capitalize font-mono">{user?.role}</div>
          </div>
          <button
            onClick={logout}
            className="rounded-md p-1.5 text-dim hover:bg-elevated hover:text-crit transition-colors"
            aria-label="Log out"
            title="Log out"
          >
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </aside>
  );
}
