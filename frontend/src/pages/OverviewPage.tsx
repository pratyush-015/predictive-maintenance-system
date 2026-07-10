import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Battery, BatteryCharging, Cpu, HardDrive, Thermometer } from "lucide-react";
import { useDashboardData } from "../store/dashboardData";
import { PulseStrip } from "../components/dashboard/PulseStrip";
import { Gauge } from "../components/dashboard/Gauge";
import { LiveChart } from "../components/dashboard/LiveChart";
import { PredictionPanel } from "../components/dashboard/PredictionPanel";
import { AlertRow } from "../components/dashboard/AlertRow";
import { ProcessTable } from "../components/dashboard/ProcessTable";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { api } from "../lib/api";
import { formatBytesRate, formatUptime, relativeTime } from "../lib/utils";
import type { Alert } from "../types";

export function OverviewPage() {
  const { history, latestMetric, latestPrediction, selectedDeviceUid, alertVersion } = useDashboardData();
  const [recentAlerts, setRecentAlerts] = useState<Alert[]>([]);

  useEffect(() => {
    if (!selectedDeviceUid) return;
    api.alerts.list({ deviceUid: selectedDeviceUid, limit: 5 }).then(setRecentAlerts);
  }, [selectedDeviceUid, alertVersion]);

  const cpuWave = history.map((m) => m.cpu_percent);

  if (!selectedDeviceUid) {
    return (
      <div className="flex h-full items-center justify-center text-mute">
        <div className="text-center">
          <p className="mb-1 font-display text-lg">No devices reporting yet</p>
          <p className="text-sm text-dim">Start the monitoring agent on a machine to see data here.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Hero pulse strip */}
      <Card className="overflow-hidden">
        <CardContent className="pt-5">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <div className="font-display text-sm text-mute">Live vitals</div>
              <div className="font-mono text-xs text-dim">
                {latestMetric ? `updated ${relativeTime(latestMetric.timestamp)}` : "waiting for data..."}
              </div>
            </div>
            {latestMetric && (
              <div className="flex items-center gap-4 text-right">
                <div className="flex items-center gap-1.5 text-xs text-dim font-mono">
                  {latestMetric.battery_plugged ? (
                    <BatteryCharging size={14} className="text-good" />
                  ) : (
                    <Battery size={14} />
                  )}
                  {latestMetric.battery_percent >= 0 ? `${latestMetric.battery_percent.toFixed(0)}%` : "n/a"}
                </div>
                <div className="text-xs text-dim font-mono">up {formatUptime(latestMetric.uptime_seconds)}</div>
              </div>
            )}
          </div>
          <PulseStrip values={cpuWave.length > 1 ? cpuWave : [0, 0]} height={72} />
        </CardContent>
      </Card>

      {/* Gauges + prediction */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>System Vitals</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <Gauge label="CPU" value={latestMetric?.cpu_percent ?? 0} />
              <Gauge label="Memory" value={latestMetric?.memory_percent ?? 0} />
              <Gauge label="Disk" value={latestMetric?.disk_percent ?? 0} />
              <Gauge
                label="Temp"
                value={latestMetric?.temperature_c ?? 0}
                unit="°C"
                thresholds={{ warn: 70, crit: 85 }}
                formatValue={(v) => Math.round(v).toString()}
              />
            </div>
            <div className="mt-5 grid grid-cols-2 gap-4 border-t border-hairline-soft pt-4 sm:grid-cols-4">
              <Stat icon={Cpu} label="CPU freq" value={`${((latestMetric?.cpu_freq_mhz ?? 0) / 1000).toFixed(2)} GHz`} />
              <Stat icon={HardDrive} label="Disk I/O" value={`${formatBytesRate(latestMetric?.disk_read_mb_s ?? 0)} / ${formatBytesRate(latestMetric?.disk_write_mb_s ?? 0)}`} />
              <Stat icon={Thermometer} label="Load (1m)" value={(latestMetric?.load_avg_1m ?? 0).toFixed(2)} />
              <Stat icon={Cpu} label="Net I/O" value={`${formatBytesRate(latestMetric?.net_recv_mb_s ?? 0)} / ${formatBytesRate(latestMetric?.net_sent_mb_s ?? 0)}`} />
            </div>
          </CardContent>
        </Card>

        <PredictionPanel prediction={latestPrediction} />
      </div>

      {/* Live charts */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>CPU &amp; Memory</CardTitle>
          </CardHeader>
          <CardContent>
            <LiveChart
              data={history}
              yDomain={[0, 100]}
              series={[
                { key: "cpu_percent", label: "CPU %", color: "var(--color-signal)" },
                { key: "memory_percent", label: "Memory %", color: "var(--color-violet)" },
              ]}
            />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Disk &amp; Network</CardTitle>
          </CardHeader>
          <CardContent>
            <LiveChart
              data={history}
              series={[
                { key: "disk_read_mb_s", label: "Disk read MB/s", color: "var(--color-info)" },
                { key: "net_recv_mb_s", label: "Net recv MB/s", color: "var(--color-warn)" },
              ]}
            />
          </CardContent>
        </Card>
      </div>

      {/* Alerts + processes */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Recent Alerts</CardTitle>
          </CardHeader>
          <CardContent>
            {recentAlerts.length === 0 ? (
              <p className="text-sm text-dim">No alerts. All quiet.</p>
            ) : (
              <div className="space-y-2">
                {recentAlerts.map((a, i) => (
                  <motion.div key={a.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.03 }}>
                    <AlertRow alert={a} />
                  </motion.div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
        <ProcessTable metric={latestMetric} />
      </div>
    </div>
  );
}

function Stat({ icon: Icon, label, value }: { icon: typeof Cpu; label: string; value: string }) {
  return (
    <div className="flex items-center gap-2.5">
      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-hairline/40 text-mute">
        <Icon size={15} />
      </div>
      <div>
        <div className="font-mono text-sm text-ink">{value}</div>
        <div className="text-[11px] text-dim">{label}</div>
      </div>
    </div>
  );
}
