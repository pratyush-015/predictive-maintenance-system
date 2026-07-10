import { Server, Clock } from "lucide-react";
import { useDashboardData } from "../store/dashboardData";
import { Card, CardContent } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { relativeTime } from "../lib/utils";

export function DevicesPage() {
  const { devices, selectedDeviceUid, setSelectedDeviceUid } = useDashboardData();

  if (devices.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-center text-mute">
        <div>
          <p className="mb-1 font-display text-lg">No devices yet</p>
          <p className="text-sm text-dim">Devices appear automatically once the monitoring agent starts reporting.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {devices.map((d) => (
        <Card
          key={d.id}
          onClick={() => setSelectedDeviceUid(d.device_uid)}
          className={`cursor-pointer transition-colors hover:border-signal/40 ${
            d.device_uid === selectedDeviceUid ? "border-signal/60" : ""
          }`}
        >
          <CardContent className="pt-5">
            <div className="mb-3 flex items-start justify-between">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-signal/10 text-signal">
                <Server size={18} />
              </div>
              <Badge variant={d.is_active ? "good" : "neutral"}>{d.is_active ? "active" : "inactive"}</Badge>
            </div>
            <div className="font-display font-semibold text-ink">{d.hostname}</div>
            <div className="mt-0.5 truncate text-xs text-dim font-mono">{d.os_info}</div>
            <div className="mt-3 flex items-center justify-between text-xs">
              <Badge variant="neutral">{d.device_type}</Badge>
              <span className="flex items-center gap-1 text-dim font-mono">
                <Clock size={11} />
                {relativeTime(d.last_seen)}
              </span>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
