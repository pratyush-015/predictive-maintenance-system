import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Award, RefreshCw } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { api } from "../lib/api";
import type { ModelComparisonOut } from "../types";

const METRIC_COLORS: Record<string, string> = {
  accuracy: "var(--color-signal)",
  precision: "var(--color-violet)",
  recall: "var(--color-info)",
  f1_score: "var(--color-warn)",
  roc_auc: "var(--color-good)",
};

export function ModelComparisonPage() {
  const [data, setData] = useState<ModelComparisonOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [reloading, setReloading] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const result = await api.predictions.modelComparison();
      setData(result);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleReload() {
    setReloading(true);
    try {
      await api.predictions.reloadModels();
      await load();
    } finally {
      setReloading(false);
    }
  }

  if (loading) return <p className="text-sm text-dim">Loading model comparison...</p>;

  if (!data || data.models.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <p className="font-display text-sm text-mute">No trained models found</p>
          <p className="mt-1 text-xs text-dim">
            Run <code className="font-mono text-signal">python ml/train_baseline.py</code> and{" "}
            <code className="font-mono text-signal">python ml/train_deep.py</code>, then reload.
          </p>
          <Button className="mt-4" size="sm" onClick={handleReload} disabled={reloading}>
            <RefreshCw size={14} className={reloading ? "animate-spin" : ""} />
            Reload models
          </Button>
        </CardContent>
      </Card>
    );
  }

  const chartData = data.models.map((m) => ({
    name: m.model_name,
    accuracy: m.accuracy,
    precision: m.precision,
    recall: m.recall,
    f1_score: m.f1_score,
    roc_auc: m.roc_auc,
  }));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <p className="text-sm text-mute">
          Trained {new Date(data.generated_at).toLocaleString()} · {data.models.length} models evaluated on
          held-out anomaly detection task
        </p>
        <Button size="sm" variant="secondary" onClick={handleReload} disabled={reloading}>
          <RefreshCw size={14} className={reloading ? "animate-spin" : ""} />
          Reload
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Metric Comparison</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={chartData} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-hairline)" vertical={false} />
              <XAxis
                dataKey="name"
                tick={{ fill: "var(--color-dim)", fontSize: 11, fontFamily: "JetBrains Mono" }}
                axisLine={{ stroke: "var(--color-hairline)" }}
                tickLine={false}
              />
              <YAxis
                domain={[0, 1]}
                tick={{ fill: "var(--color-dim)", fontSize: 11, fontFamily: "JetBrains Mono" }}
                axisLine={false}
                tickLine={false}
                width={36}
              />
              <Tooltip
                contentStyle={{
                  background: "var(--color-elevated)",
                  border: "1px solid var(--color-hairline)",
                  borderRadius: 8,
                  fontSize: 12,
                }}
              />
              <Legend wrapperStyle={{ fontSize: 12, fontFamily: "JetBrains Mono" }} />
              {Object.entries(METRIC_COLORS).map(([key, color]) => (
                <Bar key={key} dataKey={key} fill={color} radius={[3, 3, 0, 0]} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Full Metrics</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-hairline text-left text-xs text-dim">
                  <th className="pb-2 pr-4 font-medium">Model</th>
                  <th className="pb-2 pr-4 font-medium">Accuracy</th>
                  <th className="pb-2 pr-4 font-medium">Precision</th>
                  <th className="pb-2 pr-4 font-medium">Recall</th>
                  <th className="pb-2 pr-4 font-medium">F1</th>
                  <th className="pb-2 pr-4 font-medium">ROC-AUC</th>
                  <th className="pb-2 font-medium">Inference</th>
                </tr>
              </thead>
              <tbody className="font-mono">
                {data.models.map((m) => (
                  <tr key={m.model_name} className="border-b border-hairline-soft">
                    <td className="py-2.5 pr-4 font-sans">
                      <div className="flex items-center gap-2">
                        {m.model_name === data.best_model && <Award size={14} className="text-warn" />}
                        {m.model_name}
                      </div>
                    </td>
                    <td className="py-2.5 pr-4">{m.accuracy.toFixed(3)}</td>
                    <td className="py-2.5 pr-4">{m.precision.toFixed(3)}</td>
                    <td className="py-2.5 pr-4">{m.recall.toFixed(3)}</td>
                    <td className="py-2.5 pr-4">{m.f1_score.toFixed(3)}</td>
                    <td className="py-2.5 pr-4">{m.roc_auc.toFixed(3)}</td>
                    <td className="py-2.5">{m.inference_time_ms.toFixed(2)}ms</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-4 flex items-center gap-2">
            <span className="text-xs text-dim">Best model by F1:</span>
            <Badge variant="signal">{data.best_model}</Badge>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
