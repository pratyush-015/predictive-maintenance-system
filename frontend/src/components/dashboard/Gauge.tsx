import { motion } from "framer-motion";
import { cn } from "../../lib/utils";

interface GaugeProps {
  value: number; // 0-100
  label: string;
  unit?: string;
  size?: number;
  thresholds?: { warn: number; crit: number };
  formatValue?: (v: number) => string;
}

const RADIUS = 42;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
const ARC_FRACTION = 0.75; // 270° arc, oscilloscope-dial style

function colorFor(value: number, thresholds: { warn: number; crit: number }): string {
  if (value >= thresholds.crit) return "var(--color-crit)";
  if (value >= thresholds.warn) return "var(--color-warn)";
  return "var(--color-signal)";
}

export function Gauge({
  value,
  label,
  unit = "%",
  size = 128,
  thresholds = { warn: 70, crit: 90 },
  formatValue,
}: GaugeProps) {
  const clamped = Math.max(0, Math.min(100, value));
  const color = colorFor(clamped, thresholds);
  const arcLength = CIRCUMFERENCE * ARC_FRACTION;
  const offset = arcLength - (clamped / 100) * arcLength;
  const rotation = 135; // start angle so the 270° arc opens at the bottom

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} viewBox="0 0 100 100" className="-rotate-0">
          <circle
            cx="50"
            cy="50"
            r={RADIUS}
            fill="none"
            stroke="var(--color-hairline)"
            strokeWidth="7"
            strokeLinecap="round"
            strokeDasharray={`${arcLength} ${CIRCUMFERENCE}`}
            transform={`rotate(${rotation} 50 50)`}
          />
          <motion.circle
            cx="50"
            cy="50"
            r={RADIUS}
            fill="none"
            stroke={color}
            strokeWidth="7"
            strokeLinecap="round"
            strokeDasharray={`${arcLength} ${CIRCUMFERENCE}`}
            initial={false}
            animate={{ strokeDashoffset: offset }}
            transition={{ type: "spring", stiffness: 60, damping: 16 }}
            transform={`rotate(${rotation} 50 50)`}
            style={{ filter: `drop-shadow(0 0 6px ${color}66)` }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-mono font-semibold text-ink" style={{ fontSize: size * 0.19 }}>
            {formatValue ? formatValue(clamped) : Math.round(clamped)}
            {!formatValue && <span className="text-xs text-mute">{unit}</span>}
          </span>
        </div>
      </div>
      <span className="text-xs font-medium text-mute uppercase tracking-wide">{label}</span>
    </div>
  );
}

export function MiniGauge({ value, className }: { value: number; className?: string }) {
  const clamped = Math.max(0, Math.min(100, value));
  const color = clamped >= 90 ? "var(--color-crit)" : clamped >= 70 ? "var(--color-warn)" : "var(--color-signal)";
  return (
    <div className={cn("h-1.5 w-full overflow-hidden rounded-full bg-hairline", className)}>
      <motion.div
        className="h-full rounded-full"
        style={{ backgroundColor: color }}
        initial={false}
        animate={{ width: `${clamped}%` }}
        transition={{ type: "spring", stiffness: 80, damping: 20 }}
      />
    </div>
  );
}
