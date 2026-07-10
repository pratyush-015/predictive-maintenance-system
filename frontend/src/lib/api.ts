import type {
  Alert,
  Device,
  Incident,
  Metric,
  ModelComparisonOut,
  Prediction,
  User,
} from "../types";
import { tokenStore } from "./tokenStore";

export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const API_V1 = `${API_BASE}/api/v1`;

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

let refreshPromise: Promise<boolean> | null = null;

async function tryRefresh(): Promise<boolean> {
  const refresh = tokenStore.getRefresh();
  if (!refresh) return false;
  if (!refreshPromise) {
    refreshPromise = fetch(`${API_V1}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    })
      .then(async (res) => {
        if (!res.ok) return false;
        const data = await res.json();
        tokenStore.set(data.access_token, data.refresh_token);
        return true;
      })
      .catch(() => false)
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

async function request<T>(path: string, options: RequestInit = {}, retry = true): Promise<T> {
  const token = tokenStore.getAccess();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_V1}${path}`, { ...options, headers });

  if (res.status === 401 && retry) {
    const refreshed = await tryRefresh();
    if (refreshed) return request<T>(path, options, false);
    tokenStore.clear();
    window.location.href = "/login";
    throw new ApiError(401, "Session expired");
  }

  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      message = body.detail || message;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, message);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  auth: {
    login: (username: string, password: string) =>
      request<{ access_token: string; refresh_token: string }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      }),
    register: (username: string, email: string, password: string) =>
      request<User>("/auth/register", {
        method: "POST",
        body: JSON.stringify({ username, email, password, role: "viewer" }),
      }),
    me: () => request<User>("/auth/me"),
  },
  devices: {
    list: () => request<Device[]>("/devices"),
  },
  metrics: {
    latest: (deviceUid?: string) =>
      request<Metric | null>(`/metrics/latest${deviceUid ? `?device_uid=${deviceUid}` : ""}`),
    history: (deviceUid?: string, limit = 200) =>
      request<Metric[]>(
        `/metrics/history?limit=${limit}${deviceUid ? `&device_uid=${deviceUid}` : ""}`
      ),
  },
  predictions: {
    list: (deviceUid?: string, anomaliesOnly = false, limit = 100) =>
      request<Prediction[]>(
        `/predictions?limit=${limit}&anomalies_only=${anomaliesOnly}${
          deviceUid ? `&device_uid=${deviceUid}` : ""
        }`
      ),
    modelComparison: () => request<ModelComparisonOut>("/predictions/model-comparison"),
    reloadModels: () => request<{ status: string; models_loaded: string[] }>("/predictions/reload-models", {
      method: "POST",
    }),
  },
  alerts: {
    list: (params: { deviceUid?: string; unresolvedOnly?: boolean; severity?: string; limit?: number } = {}) => {
      const q = new URLSearchParams();
      if (params.deviceUid) q.set("device_uid", params.deviceUid);
      if (params.unresolvedOnly) q.set("unresolved_only", "true");
      if (params.severity) q.set("severity", params.severity);
      q.set("limit", String(params.limit ?? 100));
      return request<Alert[]>(`/alerts?${q.toString()}`);
    },
    resolve: (id: number) => request<Alert>(`/alerts/${id}/resolve`, { method: "POST" }),
  },
  incidents: {
    list: (deviceUid?: string) =>
      request<Incident[]>(`/incidents${deviceUid ? `?device_uid=${deviceUid}` : ""}`),
  },
};

export { ApiError };
