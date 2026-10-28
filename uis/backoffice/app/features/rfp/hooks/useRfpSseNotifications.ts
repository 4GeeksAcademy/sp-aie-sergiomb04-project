"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  calculateProgressiveBackoff,
  connectRfpSseWithFetch,
  deduplicateRfpTickets,
  normalizeRfpTicketPayload,
  RFPTicketSSEPayload,
  RFPTicketUIItem,
} from "../services/rfp-sse";

export type SseConnectionState =
  | "connecting"
  | "connected"
  | "reconnecting"
  | "disconnected"
  | "error";

export interface UseRfpSseNotificationsOptions {
  initialToken?: string | null;
  streamUrl?: string;
  recoveryUrl?: string;
  baseBackoffMs?: number;
  maxBackoffMs?: number;
  onNewTicket?: (ticket: RFPTicketUIItem) => void;
}

export interface UseRfpSseNotificationsResult {
  tickets: RFPTicketUIItem[];
  latestLiveTicket: RFPTicketUIItem | null;
  connectionState: SseConnectionState;
  retryAttempt: number;
  nextRetryDelayMs: number | null;
  lastEventId: string | null;
  errorMessage: string | null;
  dismissLatestAlert: () => void;
  manualReconnect: () => void;
  refreshMissedTickets: () => Promise<void>;
}

export function useRfpSseNotifications({
  initialToken = null,
  streamUrl = "/api/rfp/stream",
  recoveryUrl = "/api/rfp",
  baseBackoffMs = 1000,
  maxBackoffMs = 30000,
  onNewTicket,
}: UseRfpSseNotificationsOptions = {}): UseRfpSseNotificationsResult {
  const [tickets, setTickets] = useState<RFPTicketUIItem[]>([]);
  const [latestLiveTicket, setLatestLiveTicket] =
    useState<RFPTicketUIItem | null>(null);
  const [connectionState, setConnectionState] =
    useState<SseConnectionState>("connecting");
  const [retryAttempt, setRetryAttempt] = useState(0);
  const [nextRetryDelayMs, setNextRetryDelayMs] = useState<number | null>(null);
  const [lastEventId, setLastEventId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [reconnectTrigger, setReconnectTrigger] = useState(0);

  const tokenRef = useRef<string | null>(initialToken);
  const lastEventIdRef = useRef<string | null>(null);
  const seenEventIdsRef = useRef<Set<string>>(new Set());
  const seenTicketIdsRef = useRef<Set<string>>(new Set());
  const onNewTicketRef = useRef(onNewTicket);

  useEffect(() => {
    onNewTicketRef.current = onNewTicket;
  }, [onNewTicket]);

  useEffect(() => {
    if (initialToken) {
      tokenRef.current = initialToken;
    }
  }, [initialToken]);

  const resolveJwtToken = useCallback(async (): Promise<string | null> => {
    if (tokenRef.current) {
      return tokenRef.current;
    }
    try {
      const res = await fetch("/api/auth/token", { cache: "no-store" });
      if (res.ok) {
        const data = (await res.json()) as { access_token?: string };
        if (data.access_token) {
          tokenRef.current = data.access_token;
          return data.access_token;
        }
      }
    } catch {
      // Fall through
    }
    return null;
  }, []);

  const refreshMissedTickets = useCallback(async () => {
    const jwt = await resolveJwtToken();
    const headers: Record<string, string> = {};
    if (jwt) {
      headers.Authorization = `Bearer ${jwt}`;
    }

    try {
      const res = await fetch(recoveryUrl, {
        method: "GET",
        headers,
        cache: "no-store",
      });
      if (!res.ok) {
        return;
      }
      const list = (await res.json()) as RFPTicketSSEPayload[];
      if (!Array.isArray(list)) {
        return;
      }

      const normalizedList = list
        .filter((item) => Boolean(item && item.ticket_id))
        .map((item) =>
          normalizeRfpTicketPayload(item, { isLiveNotification: false })
        );

      for (const item of normalizedList) {
        seenTicketIdsRef.current.add(item.ticket_id);
        if (item.event_id) {
          seenEventIdsRef.current.add(item.event_id);
        }
      }

      if (normalizedList.length > 0 && !lastEventIdRef.current) {
        const newest = normalizedList[0];
        const resolvedId = newest.event_id || `evt-${newest.ticket_id}`;
        lastEventIdRef.current = resolvedId;
        setLastEventId(resolvedId);
      }

      setTickets((prev) => deduplicateRfpTickets(prev, normalizedList));
    } catch {
      // Ignore transient refetch errors during offline recovery
    }
  }, [recoveryUrl, resolveJwtToken]);

  useEffect(() => {
    let isMounted = true;
    let activeAbortController: AbortController | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    let currentAttempt = 0;

    const connectLoop = async () => {
      if (!isMounted) return;

      setConnectionState(currentAttempt === 0 ? "connecting" : "reconnecting");

      // 1. Recover any missed events before/upon reconnecting and deduplicate
      await refreshMissedTickets();
      if (!isMounted) return;

      const jwt = await resolveJwtToken();
      if (!jwt) {
        if (!isMounted) return;
        setConnectionState("error");
        setErrorMessage(
          "No se encontró un JWT válido de sesión para autenticar el stream SSE."
        );
        return;
      }

      activeAbortController = new AbortController();

      try {
        await connectRfpSseWithFetch({
          url: streamUrl,
          jwtToken: jwt,
          lastEventId: lastEventIdRef.current,
          signal: activeAbortController.signal,
          onOpen: () => {
            if (!isMounted) return;
            currentAttempt = 0;
            setRetryAttempt(0);
            setNextRetryDelayMs(null);
            setErrorMessage(null);
            setConnectionState("connected");
          },
          onTicketCreated: (incomingTicket, eventId) => {
            if (!isMounted) return;

            if (eventId) {
              lastEventIdRef.current = eventId;
              setLastEventId(eventId);
            }

            const isDuplicateEvent =
              (eventId && seenEventIdsRef.current.has(eventId)) ||
              seenTicketIdsRef.current.has(incomingTicket.ticket_id);

            if (eventId) {
              seenEventIdsRef.current.add(eventId);
            }
            seenTicketIdsRef.current.add(incomingTicket.ticket_id);

            setTickets((prev) => deduplicateRfpTickets(prev, [incomingTicket]));

            if (!isDuplicateEvent) {
              setLatestLiveTicket(incomingTicket);
              onNewTicketRef.current?.(incomingTicket);
            }
          },
        });

        // If the stream closed cleanly without abort, schedule progressive backoff reconnect
        if (isMounted && !activeAbortController.signal.aborted) {
          scheduleReconnect("Conexión SSE cerrada por el servidor. Reconectando...");
        }
      } catch (err) {
        if (!isMounted || activeAbortController.signal.aborted) {
          return;
        }
        const msg =
          err instanceof Error
            ? err.message
            : "Interrupción de red en el stream SSE";
        scheduleReconnect(msg);
      }
    };

    const scheduleReconnect = (reason: string) => {
      if (!isMounted) return;
      const delayMs = calculateProgressiveBackoff(
        currentAttempt,
        baseBackoffMs,
        maxBackoffMs
      );
      currentAttempt += 1;
      setRetryAttempt(currentAttempt);
      setNextRetryDelayMs(delayMs);
      setErrorMessage(reason);
      setConnectionState("reconnecting");

      retryTimer = setTimeout(() => {
        void connectLoop();
      }, delayMs);
    };

    void connectLoop();

    return () => {
      isMounted = false;
      if (retryTimer) {
        clearTimeout(retryTimer);
      }
      if (activeAbortController) {
        activeAbortController.abort();
      }
    };
  }, [
    baseBackoffMs,
    maxBackoffMs,
    reconnectTrigger,
    refreshMissedTickets,
    resolveJwtToken,
    streamUrl,
  ]);

  const dismissLatestAlert = useCallback(() => {
    setLatestLiveTicket(null);
  }, []);

  const manualReconnect = useCallback(() => {
    setRetryAttempt(0);
    setNextRetryDelayMs(null);
    setErrorMessage(null);
    setReconnectTrigger((prev) => prev + 1);
  }, []);

  return {
    tickets,
    latestLiveTicket,
    connectionState,
    retryAttempt,
    nextRetryDelayMs,
    lastEventId,
    errorMessage,
    dismissLatestAlert,
    manualReconnect,
    refreshMissedTickets,
  };
}
