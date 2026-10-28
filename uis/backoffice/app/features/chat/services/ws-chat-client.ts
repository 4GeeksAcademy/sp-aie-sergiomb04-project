/**
 * Real-time WebSocket Chat Client & State Reducer for TrackFlow Support Agent (Part 2).
 *
 * Responsibilities:
 * - Persistent bidirectional WebSocket connection per `session_id` / `thread_id`.
 * - Backoffice JWT authentication on handshake (`?token=...` and `auth` frame).
 * - Progressive (exponential) backoff calculation for automatic reconnection.
 * - Rehydration of conversation history and LangGraph checkpoint (`session_rehydrated`)
 *   before accepting new `token_chunk` events.
 * - Token-by-token live accumulation (`token_chunk`) and mid-stream interruption
 *   (`interrupt` -> `generation_interrupted` + new assistant turn on `new_input`).
 */

export type ChatMessageStatus = "streaming" | "completed" | "interrupted";
export type ChatRole = "user" | "assistant";

export interface ChatMessage {
  id: string;
  message_id: string;
  turn_id: string;
  session_id: string;
  thread_id: string;
  role: ChatRole;
  content: string;
  status: ChatMessageStatus;
  interrupted?: boolean;
  created_at: string;
  updated_at?: string;
  source_route?: string | null;
  tool_used?: string | null;
  nodes_executed?: string[];
  run_id?: string | null;
}

export interface CheckpointSnapshot {
  has_checkpoint: boolean;
  thread_id?: string;
  values?: Record<string, unknown>;
  next?: string[];
}

export interface WsServerEvent {
  type?: string;
  event?: string;
  session_id?: string;
  thread_id?: string;
  turn_id?: string;
  message_id?: string;
  run_id?: string;
  role?: ChatRole;
  token?: string;
  chunk?: string;
  delta?: string;
  content?: string;
  answer?: string;
  partial_content?: string;
  accumulated_content?: string;
  new_input?: string | null;
  status?: string;
  interrupted?: boolean;
  messages?: ChatMessage[];
  checkpoint?: CheckpointSnapshot;
  source_route?: string | null;
  tool_used?: string | null;
  nodes_executed?: string[];
  detail?: string;
  timestamp?: string;
}

export type WsConnectionStatus =
  | "connecting"
  | "connected"
  | "reconnecting"
  | "disconnected"
  | "error";

export interface ChatSessionState {
  sessionId: string;
  threadId: string;
  messages: ChatMessage[];
  isStreaming: boolean;
  activeTurnId: string | null;
  activeMessageId: string | null;
  checkpoint: CheckpointSnapshot | null;
  rehydrated: boolean;
  lastError: string | null;
}

/**
 * Progressive exponential backoff delay calculator (`baseDelayMs * 2^attempt` capped at `maxDelayMs`).
 */
export function calculateWsReconnectDelayMs(
  attempt: number,
  baseDelayMs: number = 1000,
  maxDelayMs: number = 30000
): number {
  const safeAttempt = Math.max(0, Math.floor(attempt));
  const exponential = baseDelayMs * Math.pow(2, safeAttempt);
  return Math.min(exponential, maxDelayMs);
}

/**
 * Build the authenticated WebSocket URL bound to `sessionId`, `threadId`, and `token`.
 */
export function buildAgentWebSocketUrl(params: {
  baseWsUrl?: string;
  sessionId: string;
  threadId?: string;
  token: string;
}): string {
  const { sessionId, token } = params;
  const threadId = params.threadId || sessionId;

  const rawBase =
    params.baseWsUrl ||
    process.env.NEXT_PUBLIC_TRACKFLOW_WS_URL ||
    process.env.NEXT_PUBLIC_TRACKFLOW_API_URL ||
    "http://127.0.0.1:8000";

  const normalizedBase = rawBase
    .trim()
    .replace(/^http:\/\//i, "ws://")
    .replace(/^https:\/\//i, "wss://")
    .replace(/\/+$/, "");

  const query = new URLSearchParams({
    session_id: sessionId,
    thread_id: threadId,
    token,
  });

  return `${normalizedBase}/agent/ws/${encodeURIComponent(sessionId)}?${query.toString()}`;
}

/**
 * Merge server-rehydrated messages with local messages without losing interrupted partial messages,
 * rolling back completed/longer local messages with stale snapshots, or duplicating existing turns.
 */
export function mergeRehydratedMessages(
  localMessages: ChatMessage[],
  serverMessages: ChatMessage[]
): ChatMessage[] {
  if (!serverMessages || serverMessages.length === 0) {
    return localMessages;
  }

  const byId = new Map<string, ChatMessage>();
  for (const msg of localMessages) {
    const key = msg.message_id || msg.id;
    byId.set(key, { ...msg, id: key, message_id: key });
  }

  for (const srv of serverMessages) {
    const key = srv.message_id || srv.id;
    const normalizedStatus: ChatMessageStatus =
      srv.status === "interrupted" || srv.interrupted
        ? "interrupted"
        : srv.status === "streaming"
          ? "streaming"
          : "completed";

    const existing = byId.get(key);
    if (existing) {
      // Never roll back a locally completed or interrupted message to a stale "streaming" snapshot
      if (
        (existing.status === "completed" || existing.status === "interrupted") &&
        normalizedStatus === "streaming"
      ) {
        continue;
      }
      // Preserve longer accumulated content if the incoming snapshot is still streaming
      const preservedContent =
        normalizedStatus === "streaming" &&
        (existing.content || "").length > (srv.content || "").length
          ? existing.content
          : srv.content;

      byId.set(key, {
        ...existing,
        ...srv,
        id: key,
        message_id: key,
        content: preservedContent,
        status: normalizedStatus,
        interrupted: normalizedStatus === "interrupted",
      });
    } else {
      byId.set(key, {
        ...srv,
        id: key,
        message_id: key,
        status: normalizedStatus,
        interrupted: normalizedStatus === "interrupted",
      });
    }
  }

  return Array.from(byId.values());
}

/**
 * Pure state reducer applying incoming WebSocket events (`session_rehydrated`, `user_message`,
 * `generation_started`, `token_chunk`, `generation_interrupted`, `generation_completed`, `error`)
 * to the chat session state.
 */
export function applyWsServerEvent(
  state: ChatSessionState,
  rawEvent: WsServerEvent
): ChatSessionState {
  const eventType = (rawEvent.event || rawEvent.type || "").trim();
  const nowIso = rawEvent.timestamp || new Date().toISOString();

  if (eventType === "session_rehydrated" || eventType === "session_state") {
    const mergedMessages = mergeRehydratedMessages(
      state.messages,
      rawEvent.messages || []
    );
    const hasStreamingMsg = mergedMessages.some((m) => m.status === "streaming");
    return {
      ...state,
      sessionId: rawEvent.session_id || state.sessionId,
      threadId: rawEvent.thread_id || state.threadId,
      messages: mergedMessages,
      isStreaming: rawEvent.status === "streaming" || hasStreamingMsg,
      activeTurnId: rawEvent.turn_id || state.activeTurnId,
      activeMessageId: rawEvent.message_id || state.activeMessageId,
      checkpoint: rawEvent.checkpoint ?? state.checkpoint,
      rehydrated: true,
      lastError: null,
    };
  }

  if (eventType === "user_message") {
    const msgId = rawEvent.message_id || `msg_user_${Date.now()}`;
    const turnId = rawEvent.turn_id || `turn_${Date.now()}`;
    const content = rawEvent.content || "";

    // Deduplicate if optimistic user message with same ID or same content at tail exists
    const existingIdx = state.messages.findIndex(
      (m) =>
        m.message_id === msgId ||
        (m.role === "user" &&
          m.content === content &&
          m.turn_id.startsWith("optimistic_"))
    );

    const updatedUserMsg: ChatMessage = {
      id: msgId,
      message_id: msgId,
      turn_id: turnId,
      session_id: rawEvent.session_id || state.sessionId,
      thread_id: rawEvent.thread_id || state.threadId,
      role: "user",
      content,
      status: "completed",
      interrupted: false,
      created_at: nowIso,
      updated_at: nowIso,
    };

    const nextMessages = [...state.messages];
    if (existingIdx >= 0) {
      nextMessages[existingIdx] = updatedUserMsg;
    } else {
      nextMessages.push(updatedUserMsg);
    }

    return {
      ...state,
      messages: nextMessages,
      lastError: null,
    };
  }

  if (eventType === "generation_started") {
    const msgId = rawEvent.message_id || `msg_asst_${Date.now()}`;
    const turnId = rawEvent.turn_id || `turn_${Date.now()}`;
    const exists = state.messages.some((m) => m.message_id === msgId);

    const nextMessages = exists
      ? state.messages
      : [
          ...state.messages,
          {
            id: msgId,
            message_id: msgId,
            turn_id: turnId,
            session_id: rawEvent.session_id || state.sessionId,
            thread_id: rawEvent.thread_id || state.threadId,
            role: "assistant" as const,
            content: "",
            status: "streaming" as const,
            interrupted: false,
            created_at: nowIso,
            updated_at: nowIso,
          },
        ];

    return {
      ...state,
      messages: nextMessages,
      isStreaming: true,
      activeTurnId: turnId,
      activeMessageId: msgId,
      lastError: null,
    };
  }

  if (eventType === "token_chunk") {
    const msgId =
      rawEvent.message_id || state.activeMessageId || `msg_asst_${Date.now()}`;
    const turnId =
      rawEvent.turn_id || state.activeTurnId || `turn_${Date.now()}`;
    const delta =
      rawEvent.token ?? rawEvent.chunk ?? rawEvent.delta ?? rawEvent.content ?? "";

    // Ignore late chunks if this message was already marked as interrupted
    const targetMsg = state.messages.find((m) => m.message_id === msgId);
    if (targetMsg && targetMsg.status === "interrupted") {
      return state;
    }

    let found = false;
    const nextMessages = state.messages.map((m) => {
      if (m.message_id === msgId) {
        found = true;
        return {
          ...m,
          content: m.content + delta,
          status: "streaming" as const,
          updated_at: nowIso,
        };
      }
      return m;
    });

    if (!found) {
      nextMessages.push({
        id: msgId,
        message_id: msgId,
        turn_id: turnId,
        session_id: rawEvent.session_id || state.sessionId,
        thread_id: rawEvent.thread_id || state.threadId,
        role: "assistant",
        content: delta,
        status: "streaming",
        interrupted: false,
        created_at: nowIso,
        updated_at: nowIso,
      });
    }

    return {
      ...state,
      messages: nextMessages,
      isStreaming: true,
      activeTurnId: turnId,
      activeMessageId: msgId,
    };
  }

  if (eventType === "generation_interrupted") {
    const msgId = rawEvent.message_id || state.activeMessageId;
    const turnId = rawEvent.turn_id || state.activeTurnId;

    const nextMessages = state.messages.map((m) => {
      if (
        (msgId && m.message_id === msgId) ||
        (turnId && m.turn_id === turnId && m.role === "assistant") ||
        (!msgId && m.role === "assistant" && m.status === "streaming")
      ) {
        const preservedContent =
          m.content || rawEvent.partial_content || rawEvent.content || "";
        return {
          ...m,
          content: preservedContent,
          status: "interrupted" as const,
          interrupted: true,
          updated_at: nowIso,
        };
      }
      return m;
    });

    const stillStreaming = nextMessages.some((m) => m.status === "streaming");
    return {
      ...state,
      messages: nextMessages,
      isStreaming: stillStreaming,
      activeTurnId: stillStreaming ? state.activeTurnId : null,
      activeMessageId: stillStreaming ? state.activeMessageId : null,
    };
  }

  if (eventType === "generation_completed") {
    const msgId =
      rawEvent.message_id || state.activeMessageId || `msg_asst_${Date.now()}`;
    const turnId =
      rawEvent.turn_id || state.activeTurnId || `turn_${Date.now()}`;
    const finalContent = rawEvent.content ?? rawEvent.answer ?? "";

    let found = false;
    const nextMessages = state.messages.map((m) => {
      if (m.message_id === msgId) {
        found = true;
        return {
          ...m,
          content: finalContent || m.content,
          status: "completed" as const,
          interrupted: false,
          source_route: rawEvent.source_route ?? m.source_route,
          tool_used: rawEvent.tool_used ?? m.tool_used,
          nodes_executed: rawEvent.nodes_executed ?? m.nodes_executed,
          run_id: rawEvent.run_id ?? m.run_id,
          updated_at: nowIso,
        };
      }
      return m;
    });

    if (!found) {
      nextMessages.push({
        id: msgId,
        message_id: msgId,
        turn_id: turnId,
        session_id: rawEvent.session_id || state.sessionId,
        thread_id: rawEvent.thread_id || state.threadId,
        role: "assistant",
        content: finalContent,
        status: "completed",
        interrupted: false,
        source_route: rawEvent.source_route,
        tool_used: rawEvent.tool_used,
        nodes_executed: rawEvent.nodes_executed,
        run_id: rawEvent.run_id,
        created_at: nowIso,
        updated_at: nowIso,
      });
    }

    return {
      ...state,
      messages: nextMessages,
      isStreaming: false,
      activeTurnId: null,
      activeMessageId: null,
    };
  }

  if (eventType === "error") {
    return {
      ...state,
      isStreaming: false,
      lastError: rawEvent.detail || "Error en la sesión de chat en tiempo real.",
    };
  }

  return state;
}
