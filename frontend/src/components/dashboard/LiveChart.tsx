import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Metric } from "../../types";

interface Series {
  key: keyof Metric;
  label: string;
  color: string;
  unit?: string;
}

interface LiveChartProps {
  data: Metric[];
  series: Series[];
  height?: number;
  yDomain?: [number, number];
}

function formatTime(iso: string): string {
  const d = new Date(iso.endsWith("Z") ? iso : iso + "Z");
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export function LiveChart({ data, series, height = 220, yDomain }: LiveChartProps) {
  const chartData = data.map((m) => ({
    ...m,
    _time: formatTime(m.timestamp),
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={chartData} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
        <defs>
          {series.map((s) => (
            <linearGradient key={s.key as string} id={`grad-${s.key as string}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={s.color} stopOpacity={0.35} />
              <stop offset="100%" stopColor={s.color} stopOpacity={0} />
            </linearGradient>
          ))}
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-hairline)" vertical={false} />
        <XAxis
          dataKey="_time"
          tick={{ fill: "var(--color-dim)", fontSize: 11, fontFamily: "JetBrains Mono" }}
          axisLine={{ stroke: "var(--color-hairline)" }}
          tickLine={false}
          minTickGap={40}
        />
        <YAxis
          domain={yDomain ?? [0, "auto"]}
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
            fontFamily: "JetBrains Mono",
          }}
          labelStyle={{ color: "var(--color-mute)" }}
        />
        {series.map((s) => (
          <Area
            key={s.key as string}
            type="monotone"
            dataKey={s.key as string}
            name={s.label}
            stroke={s.color}
            strokeWidth={2}
            fill={`url(#grad-${s.key as string})`}
            isAnimationActive={false}
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  );
}
