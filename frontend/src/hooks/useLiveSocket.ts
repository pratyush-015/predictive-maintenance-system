import { useEffect, useRef, useState } from "react";
import { API_BASE } from "../lib/api";
import { tokenStore } from "../lib/tokenStore";
import type { WsEvent } from "../types";

type ConnectionStatus = "connecting" | "open" | "closed";

export function useLiveSocket(onEvent: (event: WsEvent) => void) {
  const [status, setStatus] = useState<ConnectionStatus>("connecting");
  const handlerRef = useRef(onEvent);
  handlerRef.current = onEvent;

  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let cancelled = false;

    function connect() {
      const token = tokenStore.getAccess();
      if (!token) {
        setStatus("closed");
        return;
      }
      const wsUrl = API_BASE.replace(/^http/, "ws");
      ws = new WebSocket(`${wsUrl}/api/v1/ws/live?token=${encodeURIComponent(token)}`);
      setStatus("connecting");

      ws.onopen = () => {
        if (cancelled) return;
        setStatus("open");
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as WsEvent;
          handlerRef.current(data);
        } catch {
          /* ignore malformed frames */
        }
      };

      ws.onclose = () => {
        if (cancelled) return;
        setStatus("closed");
        reconnectTimer = setTimeout(connect, 3000);
      };

      ws.onerror = () => {
        ws?.close();
      };
    }

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      ws?.close();
    };
  }, []);

  return status;
}
