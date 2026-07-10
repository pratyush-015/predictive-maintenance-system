import { useEffect, useState } from "react";
import { GitBranch } from "lucide-react";
import { Card, CardContent } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { useDashboardData } from "../store/dashboardData";
import { api } from "../lib/api";
import { relativeTime } from "../lib/utils";
import type { Incident } from "../types";

const STATUS_VARIANT = { open: "crit", monitoring: "warn", resolved: "good" } as const;

export function IncidentsPage() {
  const { selectedDeviceUid } = useDashboardData();
  const [incidents, setIncidents] = useState<Incident[]>([]);

  useEffect(() => {
    if (!selectedDeviceUid) return;
    api.incidents.list(selectedDeviceUid).then(setIncidents);
  }, [selectedDeviceUid]);

  if (incidents.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center gap-2 py-12 text-center">
          <GitBranch className="text-dim" size={28} />
          <p className="font-display text-sm text-mute">No incidents recorded</p>
          <p className="max-w-xs text-xs text-dim">
            Incidents group related alerts into a timeline entry — they'll appear here once alert
            correlation identifies a recurring or compound issue.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="relative space-y-6 pl-6">
      <div className="absolute top-2 bottom-2 left-[7px] w-px bg-hairline" />
      {incidents.map((incident) => (
        <div key={incident.id} className="relative">
          <div
            className="absolute -left-6 top-1.5 h-3 w-3 rounded-full border-2 border-void"
            style={{ backgroundColor: `var(--color-${STATUS_VARIANT[incident.status]})` }}
          />
          <Card>
            <CardContent className="pt-5">
              <div className="flex items-center justify-between gap-3">
                <h3 className="font-display font-semibold text-ink">{incident.title}</h3>
                <Badge variant={STATUS_VARIANT[incident.status]}>{incident.status}</Badge>
              </div>
              <p className="mt-1.5 text-sm text-mute">{incident.summary}</p>
              <div className="mt-3 flex items-center gap-3 text-xs text-dim font-mono">
                <span>opened {relativeTime(incident.opened_at)}</span>
                {incident.closed_at && <span>· closed {relativeTime(incident.closed_at)}</span>}
                <span>· {incident.alert_ids.length} linked alert{incident.alert_ids.length !== 1 ? "s" : ""}</span>
              </div>
            </CardContent>
          </Card>
        </div>
      ))}
    </div>
  );
}
