export interface Metric {
  id: number;
  device_id: number;
  timestamp: string;
  cpu_percent: number;
  cpu_freq_mhz: number;
  cpu_core_count: number;
  load_avg_1m: number;
  memory_percent: number;
  memory_used_mb: number;
  memory_total_mb: number;
  swap_percent: number;
  disk_percent: number;
  disk_used_gb: number;
  disk_total_gb: number;
  disk_read_mb_s: number;
  disk_write_mb_s: number;
  net_sent_mb_s: number;
  net_recv_mb_s: number;
  temperature_c: number;
  gpu_percent: number;
  gpu_memory_percent: number;
  battery_percent: number;
  battery_plugged: boolean;
  uptime_seconds: number;
  process_count: number;
  top_processes: { pid: number; name: string; cpu_percent: number; memory_percent: number }[];
  extra: Record<string, unknown>;
}

export interface Prediction {
  id: number;
  device_id: number;
  metric_id: number;
  timestamp: string;
  model_name: string;
  is_anomaly: boolean;
  anomaly_score: number;
  predicted_issue: string;
  confidence: number;
  recommendation: string;
  explanation: Record<string, number>;
}

export interface Alert {
  id: number;
  device_id: number;
  metric_id: number | null;
  prediction_id: number | null;
  timestamp: string;
  severity: "info" | "warning" | "critical";
  category: string;
  source: "rule" | "ml";
  message: string;
  resolved: boolean;
  resolved_at: string | null;
}

export interface Incident {
  id: number;
  device_id: number;
  title: string;
  summary: string;
  severity: string;
  status: "open" | "monitoring" | "resolved";
  opened_at: string;
  closed_at: string | null;
  alert_ids: number[];
}

export interface Device {
  id: number;
  device_uid: string;
  hostname: string;
  os_info: string;
  device_type: string;
  is_active: boolean;
  last_seen: string;
}

export interface ModelComparisonEntry {
  model_name: string;
  accuracy: number;
  precision: number;
  recall: number;
  f1_score: number;
  roc_auc: number;
  inference_time_ms: number;
}

export interface ModelComparisonOut {
  generated_at: string;
  models: ModelComparisonEntry[];
  best_model: string;
}

export interface User {
  id: number;
  username: string;
  email: string;
  role: "admin" | "operator" | "viewer";
  is_active: boolean;
  created_at: string;
}

export interface WsMetricEvent {
  type: "metric";
  metric: Metric;
  prediction: Prediction | null;
  alerts: number[];
}

export interface WsAlertsEvent {
  type: "alerts";
  count: number;
}

export interface WsBatchSyncedEvent {
  type: "batch_synced";
  count: number;
}

export type WsEvent = WsMetricEvent | WsAlertsEvent | WsBatchSyncedEvent;
