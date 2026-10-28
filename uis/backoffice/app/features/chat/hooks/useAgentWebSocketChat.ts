"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  applyWsServerEvent,
  buildAgentWebSocketUrl,
  calculateWsReconnectDelayMs,
  type ChatMessage,
  type ChatSessionState,
  type WsConnectionStatus,
  type WsServerEvent,
} from "../services/ws-chat-client";

const SESSION_STORAGE_KEY = "trackflow_agent_ws_session_id";

function resolveOrCreateSessionId(initialSessionId?: string): string {
  if (initialSessionId && initialSessionId.trim()) {
    return initialSessionId.trim();
  }
  if (typeof window !== "undefined") {
    try {
      const existing = window.sessionStorage.getItem(SESSION_STORAGE_KEY);
      if (existing && existing.trim()) {
        return existing.trim();
      }
      const created = `sess_${Date.now().toString(36)}_${Math.random()
        .toString(36)
        .slice(2, 8)}`;
      window.sessionStorage.setItem(SESSION_STORAGE_KEY, created);
      return created;
    } catch {
      // Fallback if sessionStorage is restricted
    }
  }
  return `sess_${Date.now().toString(36)}`;
}

export interface UseAgentWebSocketChatOptions {
  initialSessionId?: string;
  baseWsUrl?: string;
  autoConnect?: boolean;
}

export function useAgentWebSocketChat(
  options: UseAgentWebSocketChatOptions = {}
) {
  const { initialSessionId, baseWsUrl, autoConnect = true } = options;

  const [chatState, setChatState] = useState<ChatSessionState>(() => {
    const sid = resolveOrCreateSessionId(initialSessionId);
    return {
      sessionId: sid,
      threadId: sid,
      messages: [],
      isStreaming: false,
      activeTurnId: null,
      activeMessageId: null,
      checkpoint: null,
      rehydrated: false,
      lastError: null,
    };
  });

  const [connectionStatus, setConnectionStatus] =
    useState<WsConnectionStatus>("connecting");
  const [reconnectAttempt, setReconnectAttempt] = useState<number>(0);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const unmountedRef = useRef<boolean>(false);
  const attemptRef = useRef<number>(0);
  const sessionIdRef = useRef<string>(chatState.sessionId);
  const threadIdRef = useRef<string>(chatState.threadId);
  const isRehydratedRef = useRef<boolean>(false);
  const pendingEventsBeforeRehydrationRef = useRef<WsServerEvent[]>([]);
  const connectFnRef = useRef<(() => Promise<void>) | null>(null);

  useEffect(() => {
    sessionIdRef.current = chatState.sessionId;
    threadIdRef.current = chatState.threadId;
  }, [chatState.sessionId, chatState.threadId]);

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const fetchBackofficeJwt = useCallback(async (): Promise<string | null> => {
    try {
      const res = await fetch("/api/auth/token", {
        method: "GET",
        cache: "no-store",
      });
      if (!res.ok) return null;
      const data = await res.json();
      return typeof data.access_token === "string" ? data.access_token : null;
    } catch {
      return null;
    }
  }, []);

  const rehydrateViaHttpFallback = useCallback(async (sid: string, tid: string) => {
    try {
      const res = await fetch(
        `/api/agent/sessions/${encodeURIComponent(sid)}?thread_id=${encodeURIComponent(tid)}`,
        { method: "GET", cache: "no-store" }
      );
      if (!res.ok) return;
      const payload = (await res.json()) as WsServerEvent;
      if (
        payload &&
        (payload.event === "session_rehydrated" || Array.isArray(payload.messages))
      ) {
        isRehydratedRef.current = true;
        setChatState((prev) =>
          applyWsServerEvent(prev, {
            ...payload,
            event: "session_rehydrated",
            type: "session_rehydrated",
          })
        );
      }
    } catch {
      // Ignore HTTP fallback errors; WebSocket `session_rehydrated` frame is primary
    }
  }, []);

  const connectWebSocket = useCallback(async () => {
    if (unmountedRef.current) return;
    clearReconnectTimer();

    const currentAttempt = attemptRef.current;
    setConnectionStatus(currentAttempt === 0 ? "connecting" : "reconnecting");

    const token = await fetchBackofficeJwt();
    if (unmountedRef.current) return;

    if (!token) {
      setConnectionStatus("error");
      setChatState((prev) => ({
        ...prev,
        lastError:
          "No se pudo obtener el JWT de sesión del Backoffice para autenticar el WebSocket.",
      }));
      return;
    }

    const sid = sessionIdRef.current;
    const tid = threadIdRef.current;

    if (currentAttempt > 0) {
      void rehydrateViaHttpFallback(sid, tid);
    }

    const wsUrl = buildAgentWebSocketUrl({
      baseWsUrl,
      sessionId: sid,
      threadId: tid,
      token,
    });

    try {
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
      }

      isRehydratedRef.current = false;
      pendingEventsBeforeRehydrationRef.current = [];

      const socket = new WebSocket(wsUrl);
      wsRef.current = socket;

      socket.onopen = () => {
        if (unmountedRef.current) return;
        attemptRef.current = 0;
        setReconnectAttempt(0);
        setConnectionStatus("connected");
      };

      socket.onmessage = (msgEvent: MessageEvent) => {
        if (unmountedRef.current) return;
        try {
          const parsed = JSON.parse(String(msgEvent.data)) as WsServerEvent;
          const evType = parsed.event || parsed.type;

          if (evType === "session_rehydrated" || evType === "session_state") {
            isRehydratedRef.current = true;
            setChatState((prev) => {
              let next = applyWsServerEvent(prev, parsed);
              for (const buffered of pendingEventsBeforeRehydrationRef.current) {
                next = applyWsServerEvent(next, buffered);
              }
              pendingEventsBeforeRehydrationRef.current = [];
              return next;
            });
            return;
          }

          if (!isRehydratedRef.current && evType === "token_chunk") {
            pendingEventsBeforeRehydrationRef.current.push(parsed);
            return;
          }

          setChatState((prev) => applyWsServerEvent(prev, parsed));
        } catch {
          // Ignore malformed non-JSON frames
        }
      };

      socket.onerror = () => {
        if (unmountedRef.current) return;
      };

      socket.onclose = () => {
        if (unmountedRef.current) return;
        wsRef.current = null;
        const nextAttempt = attemptRef.current + 1;
        attemptRef.current = nextAttempt;
        setReconnectAttempt(nextAttempt);
        setConnectionStatus("reconnecting");

        const delayMs = calculateWsReconnectDelayMs(nextAttempt - 1);
        reconnectTimerRef.current = setTimeout(() => {
          void connectFnRef.current?.();
        }, delayMs);
      };
    } catch {
      const nextAttempt = attemptRef.current + 1;
      attemptRef.current = nextAttempt;
      setReconnectAttempt(nextAttempt);
      setConnectionStatus("reconnecting");
      const delayMs = calculateWsReconnectDelayMs(nextAttempt - 1);
      reconnectTimerRef.current = setTimeout(() => {
        void connectFnRef.current?.();
      }, delayMs);
    }
  }, [baseWsUrl, clearReconnectTimer, fetchBackofficeJwt, rehydrateViaHttpFallback]);

  useEffect(() => {
    connectFnRef.current = connectWebSocket;
  }, [connectWebSocket]);

  useEffect(() => {
    unmountedRef.current = false;
    if (autoConnect) {
      const initialTimer = setTimeout(() => {
        void connectFnRef.current?.();
      }, 0);
      return () => {
        clearTimeout(initialTimer);
        unmountedRef.current = true;
        clearReconnectTimer();
        if (wsRef.current) {
          wsRef.current.onclose = null;
          wsRef.current.close();
          wsRef.current = null;
        }
      };
    }
    return () => {
      unmountedRef.current = true;
      clearReconnectTimer();
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [autoConnect, clearReconnectTimer]);

  const sendMessage = useCallback(
    (questionText: string) => {
      const clean = questionText.trim();
      if (!clean) return false;

      const socket = wsRef.current;
      if (!socket || socket.readyState !== WebSocket.OPEN) {
        setChatState((prev) => ({
          ...prev,
          lastError:
            "El canal WebSocket se está reconectando. Intenta de nuevo en unos instantes.",
        }));
        return false;
      }

      if (chatState.isStreaming) {
        socket.send(
          JSON.stringify({
            type: "interrupt",
            event: "interrupt",
            session_id: chatState.sessionId,
            thread_id: chatState.threadId,
            new_input: clean,
          })
        );
      } else {
        socket.send(
          JSON.stringify({
            type: "user_message",
            event: "user_message",
            session_id: chatState.sessionId,
            thread_id: chatState.threadId,
            content: clean,
          })
        );
      }
      return true;
    },
    [chatState.isStreaming, chatState.sessionId, chatState.threadId]
  );

  const interruptGeneration = useCallback(
    (newInput?: string) => {
      const socket = wsRef.current;
      const cleanRedirect = newInput ? newInput.trim() : "";

      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(
          JSON.stringify({
            type: "interrupt",
            event: "interrupt",
            session_id: chatState.sessionId,
            thread_id: chatState.threadId,
            ...(cleanRedirect ? { new_input: cleanRedirect } : {}),
          })
        );
      }

      if (!cleanRedirect) {
        setChatState((prev) =>
          applyWsServerEvent(prev, {
            event: "generation_interrupted",
            type: "generation_interrupted",
            session_id: prev.sessionId,
            thread_id: prev.threadId,
            turn_id: prev.activeTurnId ?? undefined,
            message_id: prev.activeMessageId ?? undefined,
            status: "interrupted",
            interrupted: true,
          })
        );
      }
    },
    [chatState.sessionId, chatState.threadId]
  );

  const forceReconnect = useCallback(() => {
    attemptRef.current = 0;
    setReconnectAttempt(0);
    void connectFnRef.current?.();
  }, []);

  return {
    sessionId: chatState.sessionId,
    threadId: chatState.threadId,
    messages: chatState.messages as ChatMessage[],
    isStreaming: chatState.isStreaming,
    rehydrated: chatState.rehydrated,
    checkpoint: chatState.checkpoint,
    error: chatState.lastError,
    connectionStatus,
    reconnectAttempt,
    sendMessage,
    interruptGeneration,
    forceReconnect,
  };
}
