import { Moon, Sun, Wifi, WifiOff, Loader2 } from "lucide-react";
import { useThemeStore } from "../../store/theme";
import type { Device } from "../../types";
import { cn } from "../../lib/utils";

interface TopbarProps {
  title: string;
  devices: Device[];
  selectedDeviceUid: string | null;
  onSelectDevice: (uid: string) => void;
  wsStatus: "connecting" | "open" | "closed";
}

export function Topbar({ title, devices, selectedDeviceUid, onSelectDevice, wsStatus }: TopbarProps) {
  const { theme, toggle } = useThemeStore();

  return (
    <header className="flex items-center justify-between gap-4 border-b border-hairline bg-surface/60 px-6 py-4 backdrop-blur-sm">
      <h1 className="font-display text-xl font-semibold tracking-tight">{title}</h1>

      <div className="flex items-center gap-3">
        {devices.length > 0 && (
          <select
            value={selectedDeviceUid ?? ""}
            onChange={(e) => onSelectDevice(e.target.value)}
            className="rounded-lg border border-hairline bg-elevated px-3 py-1.5 text-sm text-ink font-mono focus:border-signal outline-none"
          >
            {devices.map((d) => (
              <option key={d.device_uid} value={d.device_uid}>
                {d.hostname}
              </option>
            ))}
          </select>
        )}

        <div
          className={cn(
            "flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-mono",
            wsStatus === "open" && "border-good/30 bg-good/10 text-good",
            wsStatus === "connecting" && "border-warn/30 bg-warn/10 text-warn",
            wsStatus === "closed" && "border-crit/30 bg-crit/10 text-crit"
          )}
        >
          {wsStatus === "open" && <Wifi size={13} />}
          {wsStatus === "connecting" && <Loader2 size={13} className="animate-spin" />}
          {wsStatus === "closed" && <WifiOff size={13} />}
          {wsStatus === "open" ? "LIVE" : wsStatus === "connecting" ? "CONNECTING" : "OFFLINE"}
        </div>

        <button
          onClick={toggle}
          className="rounded-lg border border-hairline bg-elevated p-2 text-mute hover:text-ink transition-colors"
          aria-label="Toggle theme"
        >
          {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
        </button>
      </div>
    </header>
  );
}
