import { useEffect, useState } from "react";
import { AlertRow } from "../components/dashboard/AlertRow";
import { Card, CardContent } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { useDashboardData } from "../store/dashboardData";
import { api } from "../lib/api";
import type { Alert } from "../types";

export function AlertsPage() {
  const { selectedDeviceUid, alertVersion } = useDashboardData();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [unresolvedOnly, setUnresolvedOnly] = useState(true);
  const [loading, setLoading] = useState(true);

  async function refresh() {
    setLoading(true);
    try {
      const rows = await api.alerts.list({
        deviceUid: selectedDeviceUid ?? undefined,
        unresolvedOnly,
        limit: 200,
      });
      setAlerts(rows);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDeviceUid, unresolvedOnly, alertVersion]);

  async function handleResolve(id: number) {
    await api.alerts.resolve(id);
    refresh();
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-mute">{alerts.length} alert{alerts.length !== 1 ? "s" : ""}</p>
        <Button size="sm" variant={unresolvedOnly ? "primary" : "secondary"} onClick={() => setUnresolvedOnly((v) => !v)}>
          {unresolvedOnly ? "Showing unresolved" : "Showing all"}
        </Button>
      </div>

      <Card>
        <CardContent className="pt-5">
          {loading ? (
            <p className="text-sm text-dim">Loading...</p>
          ) : alerts.length === 0 ? (
            <p className="text-sm text-dim">No alerts to show.</p>
          ) : (
            <div className="space-y-2">
              {alerts.map((a) => (
                <AlertRow key={a.id} alert={a} onResolve={handleResolve} />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
