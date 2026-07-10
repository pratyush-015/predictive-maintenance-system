import type { HTMLAttributes } from "react";
import { cn } from "../../lib/utils";

type Variant = "good" | "warn" | "crit" | "info" | "neutral" | "signal";

const variantClasses: Record<Variant, string> = {
  good: "bg-good/10 text-good border-good/30",
  warn: "bg-warn/10 text-warn border-warn/30",
  crit: "bg-crit/10 text-crit border-crit/30",
  info: "bg-info/10 text-info border-info/30",
  neutral: "bg-hairline/40 text-mute border-hairline",
  signal: "bg-signal/10 text-signal border-signal/30",
};

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: Variant;
}

export function Badge({ variant = "neutral", className, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium font-mono",
        variantClasses[variant],
        className
      )}
      {...props}
    />
  );
}
