import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";

import { useAuthStore } from "@/store/auth";
import { toast } from "@/store/notifications";

/**
 * Подключение к WebSocket-уведомлениям бекенда.
 *
 * События:
 *   scan.completed { scan_id, findings_count, category }
 *   scan.failed    { scan_id, error }
 */
export function useWebSocket() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const queryClient = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<number | null>(null);

  useEffect(() => {
    if (!accessToken) return;

    let cancelled = false;

    const connect = () => {
      if (cancelled) return;

      const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
      const url = `${proto}//${window.location.host}/api/v1/ws?token=${encodeURIComponent(accessToken)}`;
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleMessage(data);
        } catch {
          /* ping/pong */
        }
      };

      ws.onclose = () => {
        if (cancelled) return;
        // Пробуем переподключиться через 5 секунд
        reconnectRef.current = window.setTimeout(connect, 5000);
      };

      ws.onerror = () => {
        ws.close();
      };
    };

    const handleMessage = (data: any) => {
      switch (data.type) {
        case "scan.completed":
          toast({
            type: "success",
            title: "Сканирование завершено",
            message: `Найдено ${data.findings_count} ПДн, категория: ${data.category ?? "—"}`,
          });
          queryClient.invalidateQueries({ queryKey: ["scans"] });
          queryClient.invalidateQueries({ queryKey: ["scan", data.scan_id] });
          break;

        case "scan.failed":
          toast({
            type: "error",
            title: "Ошибка сканирования",
            message: data.error,
          });
          queryClient.invalidateQueries({ queryKey: ["scans"] });
          break;

        case "scan.status_changed":
          queryClient.invalidateQueries({ queryKey: ["scan", data.scan_id] });
          break;
      }
    };

    connect();

    // Heartbeat — раз в 30 секунд
    const pingInterval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send("ping");
      }
    }, 30000);

    return () => {
      cancelled = true;
      clearInterval(pingInterval);
      if (reconnectRef.current) {
        clearTimeout(reconnectRef.current);
      }
      wsRef.current?.close();
    };
  }, [accessToken, queryClient]);
}
