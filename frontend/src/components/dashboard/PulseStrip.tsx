import { useMemo } from "react";

interface PulseStripProps {
  values: number[]; // recent readings, oldest first, 0-100 scale
  height?: number;
  color?: string;
  live?: boolean;
}

/**
 * The dashboard's signature element: a live waveform that reads like an
 * oscilloscope trace of the machine's vital signs. Deliberately not a
 * generic line chart — no axes, no grid, just the pulse itself, because
 * the point is glanceability, not precision (precise values live in the
 * gauges and history charts elsewhere).
 */
export function PulseStrip({ values, height = 56, color = "var(--color-signal)", live = true }: PulseStripProps) {
  const path = useMemo(() => {
    if (values.length < 2) return "";
    const w = 400;
    const h = height;
    const step = w / (values.length - 1);
    const points = values.map((v, i) => {
      const x = i * step;
      const y = h - (Math.max(0, Math.min(100, v)) / 100) * h * 0.85 - h * 0.075;
      return [x, y];
    });
    return points.map(([x, y], i) => (i === 0 ? `M ${x},${y}` : `L ${x},${y}`)).join(" ");
  }, [values, height]);

  return (
    <div className="relative w-full overflow-hidden" style={{ height }}>
      <svg viewBox={`0 0 400 ${height}`} preserveAspectRatio="none" className="h-full w-full">
        <defs>
          <linearGradient id="pulse-fade" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor={color} stopOpacity="0" />
            <stop offset="15%" stopColor={color} stopOpacity="0.9" />
            <stop offset="100%" stopColor={color} stopOpacity="0.9" />
          </linearGradient>
        </defs>
        <path d={path} fill="none" stroke="url(#pulse-fade)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        {live && values.length > 0 && (
          <circle
            cx={400}
            cy={height - (Math.max(0, Math.min(100, values[values.length - 1])) / 100) * height * 0.85 - height * 0.075}
            r="3"
            fill={color}
            className="animate-pulse-slow"
            style={{ filter: `drop-shadow(0 0 4px ${color})` }}
          />
        )}
      </svg>
    </div>
  );
}
