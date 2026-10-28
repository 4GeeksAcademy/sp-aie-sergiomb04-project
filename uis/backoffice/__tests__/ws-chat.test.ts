import {
  applyWsServerEvent,
  buildAgentWebSocketUrl,
  calculateWsReconnectDelayMs,
  mergeRehydratedMessages,
  type ChatSessionState,
} from "../app/features/chat/services/ws-chat-client";

describe("TrackFlow WebSocket Chat Client & State Reducer (Part 2)", () => {
  const createInitialState = (
    sessionId = "sess-trackflow-100"
  ): ChatSessionState => ({
    sessionId,
    threadId: sessionId,
    messages: [],
    isStreaming: false,
    activeTurnId: null,
    activeMessageId: null,
    checkpoint: null,
    rehydrated: false,
    lastError: null,
  });

  test("calculates progressive exponential backoff delays capped at maxDelayMs", () => {
    expect(calculateWsReconnectDelayMs(0, 1000, 30000)).toBe(1000);
    expect(calculateWsReconnectDelayMs(1, 1000, 30000)).toBe(2000);
    expect(calculateWsReconnectDelayMs(2, 1000, 30000)).toBe(4000);
    expect(calculateWsReconnectDelayMs(3, 1000, 30000)).toBe(8000);
    expect(calculateWsReconnectDelayMs(6, 1000, 30000)).toBe(30000);
  });

  test("builds WebSocket URL with session_id, thread_id and Backoffice JWT query params", () => {
    const url = buildAgentWebSocketUrl({
      baseWsUrl: "http://127.0.0.1:8000",
      sessionId: "sess-abc",
      threadId: "thread-abc",
      token: "jwt-token-xyz",
    });

    expect(url).toContain("ws://127.0.0.1:8000/agent/ws/sess-abc?");
    expect(url).toContain("session_id=sess-abc");
    expect(url).toContain("thread_id=thread-abc");
    expect(url).toContain("token=jwt-token-xyz");
  });

  test("accumulates token_chunk events in real time and marks completed on generation_completed", () => {
    let state = createInitialState("sess-01");

    state = applyWsServerEvent(state, {
      event: "user_message",
      session_id: "sess-01",
      thread_id: "sess-01",
      turn_id: "turn_1",
      message_id: "msg_u1",
      content: "¿Cuál es el SLA en España?",
    });

    state = applyWsServerEvent(state, {
      event: "generation_started",
      session_id: "sess-01",
      thread_id: "sess-01",
      turn_id: "turn_1",
      message_id: "msg_a1",
    });
    expect(state.isStreaming).toBe(true);

    state = applyWsServerEvent(state, {
      event: "token_chunk",
      turn_id: "turn_1",
      message_id: "msg_a1",
      token: "El SLA ",
    });
    state = applyWsServerEvent(state, {
      event: "token_chunk",
      turn_id: "turn_1",
      message_id: "msg_a1",
      token: "estándar es ",
    });
    state = applyWsServerEvent(state, {
      event: "token_chunk",
      turn_id: "turn_1",
      message_id: "msg_a1",
      token: "24-48h.",
    });

    const streamingMsg = state.messages.find((m) => m.message_id === "msg_a1");
    expect(streamingMsg?.content).toBe("El SLA estándar es 24-48h.");
    expect(streamingMsg?.status).toBe("streaming");

    state = applyWsServerEvent(state, {
      event: "generation_completed",
      turn_id: "turn_1",
      message_id: "msg_a1",
      content: "El SLA estándar es 24-48h.",
      source_route: "rag",
    });

    expect(state.isStreaming).toBe(false);
    const completedMsg = state.messages.find((m) => m.message_id === "msg_a1");
    expect(completedMsg?.status).toBe("completed");
    expect(completedMsg?.source_route).toBe("rag");
  });

  test("marks partial message as interrupted on generation_interrupted, ignores late chunks, and appends new turn on redirect", () => {
    let state = createInitialState("sess-int-01");

    state = applyWsServerEvent(state, {
      event: "user_message",
      turn_id: "turn_1",
      message_id: "msg_u1",
      content: "Pregunta original larga",
    });
    state = applyWsServerEvent(state, {
      event: "token_chunk",
      turn_id: "turn_1",
      message_id: "msg_a1",
      token: "Respuesta parcial ",
    });
    state = applyWsServerEvent(state, {
      event: "token_chunk",
      turn_id: "turn_1",
      message_id: "msg_a1",
      token: "antes del abort...",
    });

    // Interrupt arrives
    state = applyWsServerEvent(state, {
      event: "generation_interrupted",
      turn_id: "turn_1",
      message_id: "msg_a1",
      status: "interrupted",
      partial_content: "Respuesta parcial antes del abort...",
      new_input: "Mejor dime solo tarifas express",
    });

    expect(state.isStreaming).toBe(false);
    const interruptedMsg = state.messages.find((m) => m.message_id === "msg_a1");
    expect(interruptedMsg?.status).toBe("interrupted");
    expect(interruptedMsg?.interrupted).toBe(true);
    expect(interruptedMsg?.content).toBe("Respuesta parcial antes del abort...");

    // Any late chunk for msg_a1 must be ignored
    state = applyWsServerEvent(state, {
      event: "token_chunk",
      turn_id: "turn_1",
      message_id: "msg_a1",
      token: " TEXTO QUE NO DEBE ENTRAR",
    });
    expect(
      state.messages.find((m) => m.message_id === "msg_a1")?.content
    ).toBe("Respuesta parcial antes del abort...");

    // New turn starts for new_input without overwriting msg_a1
    state = applyWsServerEvent(state, {
      event: "user_message",
      turn_id: "turn_2",
      message_id: "msg_u2",
      content: "Mejor dime solo tarifas express",
    });
    state = applyWsServerEvent(state, {
      event: "token_chunk",
      turn_id: "turn_2",
      message_id: "msg_a2",
      token: "La tarifa express es 9.90 EUR.",
    });
    state = applyWsServerEvent(state, {
      event: "generation_completed",
      turn_id: "turn_2",
      message_id: "msg_a2",
      content: "La tarifa express es 9.90 EUR.",
    });

    expect(state.messages).toHaveLength(4);
    expect(state.messages[1].message_id).toBe("msg_a1");
    expect(state.messages[1].status).toBe("interrupted");
    expect(state.messages[3].message_id).toBe("msg_a2");
    expect(state.messages[3].status).toBe("completed");
    expect(state.messages[3].content).toBe("La tarifa express es 9.90 EUR.");
  });

  test("rehydrates conversation history and checkpoint on reconnect without duplicating messages", () => {
    let state = createInitialState("sess-rehydrate-99");

    state = applyWsServerEvent(state, {
      event: "session_rehydrated",
      session_id: "sess-rehydrate-99",
      thread_id: "sess-rehydrate-99",
      status: "idle",
      checkpoint: {
        has_checkpoint: true,
        thread_id: "sess-rehydrate-99",
        values: { question: "Última consulta", answer: "Última respuesta" },
      },
      messages: [
        {
          id: "msg_u1",
          message_id: "msg_u1",
          turn_id: "turn_1",
          session_id: "sess-rehydrate-99",
          thread_id: "sess-rehydrate-99",
          role: "user",
          content: "Consulta previa",
          status: "completed",
          created_at: "2026-10-23T18:00:00Z",
        },
        {
          id: "msg_a1",
          message_id: "msg_a1",
          turn_id: "turn_1",
          session_id: "sess-rehydrate-99",
          thread_id: "sess-rehydrate-99",
          role: "assistant",
          content: "Respuesta parcial cortada",
          status: "interrupted",
          interrupted: true,
          created_at: "2026-10-23T18:00:02Z",
        },
      ],
    });

    expect(state.rehydrated).toBe(true);
    expect(state.checkpoint?.has_checkpoint).toBe(true);
    expect(state.messages).toHaveLength(2);
    expect(state.messages[1].status).toBe("interrupted");

    // Re-applying the same rehydration snapshot deduplicates cleanly
    const mergedAgain = mergeRehydratedMessages(state.messages, state.messages);
    expect(mergedAgain).toHaveLength(2);
  });
});
