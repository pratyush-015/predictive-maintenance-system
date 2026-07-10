import { Card, CardContent, CardHeader, CardTitle } from "../ui/Card";
import { MiniGauge } from "./Gauge";
import type { Metric } from "../../types";

export function ProcessTable({ metric }: { metric: Metric | null }) {
  const processes = metric?.top_processes ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Top Processes</CardTitle>
        <span className="font-mono text-[11px] text-dim">{metric?.process_count ?? 0} running</span>
      </CardHeader>
      <CardContent>
        {processes.length === 0 ? (
          <p className="text-sm text-dim">No process data yet.</p>
        ) : (
          <div className="space-y-3">
            {processes.map((p) => (
              <div key={p.pid} className="flex items-center gap-3">
                <div className="w-32 truncate text-sm text-ink" title={p.name}>
                  {p.name}
                </div>
                <div className="flex-1">
                  <MiniGauge value={p.cpu_percent} />
                </div>
                <div className="w-14 text-right font-mono text-xs text-mute">{p.cpu_percent.toFixed(1)}%</div>
                <div className="w-16 text-right font-mono text-xs text-dim">pid {p.pid}</div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
