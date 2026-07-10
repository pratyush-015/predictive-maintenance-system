import { AlertTriangle, AlertOctagon, Info, Check } from "lucide-react";
import { Badge } from "../ui/Badge";
import type { Alert } from "../../types";
import { relativeTime } from "../../lib/utils";

const SEVERITY_ICON = {
  info: Info,
  warning: AlertTriangle,
  critical: AlertOctagon,
} as const;

const SEVERITY_VARIANT = {
  info: "info",
  warning: "warn",
  critical: "crit",
} as const;

interface AlertRowProps {
  alert: Alert;
  onResolve?: (id: number) => void;
}

export function AlertRow({ alert, onResolve }: AlertRowProps) {
  const Icon = SEVERITY_ICON[alert.severity];

  return (
    <div className="flex items-start gap-3 rounded-lg border border-hairline-soft bg-void/30 px-4 py-3">
      <Icon
        size={16}
        className="mt-0.5 shrink-0"
        style={{ color: `var(--color-${SEVERITY_VARIANT[alert.severity] === "crit" ? "crit" : SEVERITY_VARIANT[alert.severity] === "warn" ? "warn" : "info"})` }}
      />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 flex-wrap">
          <Badge variant={SEVERITY_VARIANT[alert.severity]}>{alert.severity}</Badge>
          <Badge variant="neutral">{alert.source === "ml" ? "ML" : "rule"}</Badge>
          <span className="text-xs text-dim font-mono">{relativeTime(alert.timestamp)}</span>
        </div>
        <p className="mt-1.5 text-sm text-ink leading-snug">{alert.message}</p>
      </div>
      {onResolve && !alert.resolved && (
        <button
          onClick={() => onResolve(alert.id)}
          className="shrink-0 rounded-md p-1.5 text-dim hover:bg-good/10 hover:text-good transition-colors"
          title="Mark resolved"
        >
          <Check size={15} />
        </button>
      )}
      {alert.resolved && <Badge variant="good">resolved</Badge>}
    </div>
  );
}
