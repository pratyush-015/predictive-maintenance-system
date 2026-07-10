import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api } from "../lib/api";
import { useLiveSocket } from "../hooks/useLiveSocket";
import type { Device, Metric, Prediction, WsEvent } from "../types";

const HISTORY_LIMIT = 120; // ~10 minutes at 5s cadence — enough for gauges + pulse + trend charts

interface DashboardDataState {
  devices: Device[];
  selectedDeviceUid: string | null;
  setSelectedDeviceUid: (uid: string) => void;
  selectedDevice: Device | null;
  history: Metric[];
  latestMetric: Metric | null;
  latestPrediction: Prediction | null;
  wsStatus: "connecting" | "open" | "closed";
  alertVersion: number; // bumped whenever a new alert arrives, pages can refetch on change
  loading: boolean;
}

const DashboardDataContext = createContext<DashboardDataState | null>(null);

export function DashboardDataProvider({ children }: { children: ReactNode }) {
  const [devices, setDevices] = useState<Device[]>([]);
  const [selectedDeviceUid, setSelectedDeviceUid] = useState<string | null>(null);
  const [history, setHistory] = useState<Metric[]>([]);
  const [latestPrediction, setLatestPrediction] = useState<Prediction | null>(null);
  const [alertVersion, setAlertVersion] = useState(0);
  const [loading, setLoading] = useState(true);

  // Initial device list + first history load
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const list = await api.devices.list();
        if (cancelled) return;
        setDevices(list);
        if (list.length > 0) {
          setSelectedDeviceUid((prev) => prev ?? list[0].device_uid);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Load history whenever the selected device changes
  useEffect(() => {
    if (!selectedDeviceUid) return;
    let cancelled = false;
    (async () => {
      const rows = await api.metrics.history(selectedDeviceUid, HISTORY_LIMIT);
      if (!cancelled) setHistory(rows);
      const preds = await api.predictions.list(selectedDeviceUid, false, 1);
      if (!cancelled && preds.length > 0) setLatestPrediction(preds[preds.length - 1]);
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedDeviceUid]);

  const handleWsEvent = useCallback(
    (event: WsEvent) => {
      if (event.type === "metric") {
        const metric = event.metric;
        setDevices((prev) => {
          const exists = prev.some((d) => d.id === metric.device_id);
          if (!exists) {
            // A brand-new device just checked in — refresh the device list.
            api.devices.list().then(setDevices);
          }
          return prev;
        });

        setHistory((prev) => {
          // Only append if it belongs to the currently selected device
          const currentDevice = devices.find((d) => d.device_uid === selectedDeviceUid);
          if (!currentDevice || metric.device_id !== currentDevice.id) return prev;
          const next = [...prev, metric];
          return next.length > HISTORY_LIMIT ? next.slice(next.length - HISTORY_LIMIT) : next;
        });

        if (event.prediction) {
          const currentDevice = devices.find((d) => d.device_uid === selectedDeviceUid);
          if (currentDevice && metric.device_id === currentDevice.id) {
            setLatestPrediction(event.prediction);
          }
        }

        if (event.alerts.length > 0) setAlertVersion((v) => v + 1);
      } else if (event.type === "alerts") {
        setAlertVersion((v) => v + 1);
      }
    },
    [devices, selectedDeviceUid]
  );

  const wsStatus = useLiveSocket(handleWsEvent);

  const selectedDevice = useMemo(
    () => devices.find((d) => d.device_uid === selectedDeviceUid) ?? null,
    [devices, selectedDeviceUid]
  );

  const latestMetric = history.length > 0 ? history[history.length - 1] : null;

  const value: DashboardDataState = {
    devices,
    selectedDeviceUid,
    setSelectedDeviceUid,
    selectedDevice,
    history,
    latestMetric,
    latestPrediction,
    wsStatus,
    alertVersion,
    loading,
  };

  return <DashboardDataContext.Provider value={value}>{children}</DashboardDataContext.Provider>;
}

export function useDashboardData() {
  const ctx = useContext(DashboardDataContext);
  if (!ctx) throw new Error("useDashboardData must be used within DashboardDataProvider");
  return ctx;
}
