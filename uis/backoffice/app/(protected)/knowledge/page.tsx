"use client";

import { useState } from "react";
import { useAgentWebSocketChat } from "@/app/features/chat/hooks/useAgentWebSocketChat";

const SUGGESTED_QUERIES = [
  {
    category: "SLA y Envíos",
    question:
      "¿Cuáles son los tiempos de entrega estándar y express en España y Estados Unidos?",
  },
  {
    category: "Picos de Demanda",
    question: "¿Cómo se gestiona el SLA de entrega durante Black Friday y rebajas?",
  },
  {
    category: "Devoluciones",
    question:
      "¿Cuál es la ventana de devolución estándar y cómo se tratan las devoluciones internacionales?",
  },
  {
    category: "Transportistas",
    question: "¿Qué transportista tiene mejor cobertura en zonas rurales de Aragón?",
  },
  {
    category: "Tarifas",
    question:
      "¿Cuáles son las tarifas de almacenamiento y qué condiciones aplican para inventario de larga duración?",
  },
  {
    category: "Negociación",
    question:
      "¿Puede un account manager autorizar un descuento de almacenamiento directamente?",
  },
];

export default function KnowledgeQueryPage() {
  const [question, setQuestion] = useState("");
  const {
    sessionId,
    threadId,
    messages,
    isStreaming,
    rehydrated,
    checkpoint,
    error,
    connectionStatus,
    reconnectAttempt,
    sendMessage,
    interruptGeneration,
    forceReconnect,
  } = useAgentWebSocketChat();

  const handleSubmit = (qToAsk?: string) => {
    const q = (qToAsk ?? question).trim();
    if (!q) return;

    const sent = sendMessage(q);
    if (sent) {
      setQuestion("");
    }
  };

  const handleInterruptOnly = () => {
    const redirectText = question.trim();
    if (redirectText) {
      interruptGeneration(redirectText);
      setQuestion("");
    } else {
      interruptGeneration();
    }
  };

  return (
    <div className="flex flex-1 flex-col gap-8 p-6 lg:p-10">
      {/* Header & Real-Time WebSocket Status Bar */}
      <div className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2.5">
            <span className="rounded-md bg-indigo-50 px-2.5 py-1 text-xs font-semibold uppercase tracking-wider text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
              Agente de Soporte · WebSocket Streaming
            </span>
            <span
              id="ws-session-badge"
              className="rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1 font-mono text-xs text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300"
            >
              session_id: {sessionId}
            </span>
            {rehydrated && (
              <span className="rounded-md bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300">
                {checkpoint?.has_checkpoint
                  ? "Hilo rehidratado (Checkpoint activo)"
                  : "Sesión sincronizada"}
              </span>
            )}
          </div>

          {/* Connection indicator */}
          <div className="flex items-center gap-2">
            <span
              id="ws-connection-badge"
              className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${
                connectionStatus === "connected"
                  ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300"
                  : connectionStatus === "reconnecting" ||
                      connectionStatus === "connecting"
                    ? "bg-amber-50 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300"
                    : "bg-rose-50 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300"
              }`}
            >
              <span
                className={`h-2 w-2 rounded-full ${
                  connectionStatus === "connected"
                    ? "bg-emerald-500"
                    : connectionStatus === "reconnecting" ||
                        connectionStatus === "connecting"
                      ? "animate-pulse bg-amber-500"
                      : "bg-rose-500"
                }`}
              />
              {connectionStatus === "connected"
                ? "WebSocket Conectado"
                : connectionStatus === "connecting"
                  ? "Conectando WebSocket..."
                  : connectionStatus === "reconnecting"
                    ? `Reconectando (intento #${reconnectAttempt})...`
                    : "WebSocket Desconectado"}
            </span>
            {connectionStatus !== "connected" && (
              <button
                type="button"
                onClick={forceReconnect}
                className="rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
              >
                Reconectar ahora
              </button>
            )}
          </div>
        </div>

        <h1 className="text-2xl font-semibold tracking-tight text-slate-950 dark:text-white">
          Asistente Comercial y Operativo en Tiempo Real
        </h1>
        <p className="max-w-3xl text-sm text-slate-600 dark:text-slate-400">
          Conversa en tiempo real token por token con el agente de soporte de TrackFlow
          (hilo <code className="font-mono text-xs">{threadId}</code>). Puedes{" "}
          <strong>interrumpir y redirigir</strong> al agente a mitad de una respuesta sin
          esperar a que termine.
        </p>
      </div>

      {/* Conversation History Stream */}
      <div
        id="rag-answer-box"
        className="flex min-h-[340px] flex-col gap-4 rounded-2xl border border-slate-200 bg-gradient-to-b from-white to-slate-50/70 p-6 shadow-sm dark:border-slate-800 dark:from-slate-900 dark:to-slate-900/80"
      >
        <div className="flex items-center justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
          <div className="flex items-center gap-2">
            <span
              className={`flex h-2.5 w-2.5 rounded-full ${
                isStreaming ? "animate-ping bg-indigo-500" : "bg-emerald-500"
              }`}
            />
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400">
              {isStreaming
                ? "Transmitiendo tokens en vivo (token_chunk)..."
                : "Hilo de Conversación Persistente"}
            </span>
          </div>
          <span className="text-xs text-slate-400">
            {messages.length} {messages.length === 1 ? "mensaje" : "mensajes"}
          </span>
        </div>

        {messages.length === 0 ? (
          <div className="flex flex-1 flex-col items-center justify-center py-12 text-center">
            <p className="text-sm font-medium text-slate-600 dark:text-slate-300">
              No hay mensajes en esta sesión todavía.
            </p>
            <p className="mt-1 max-w-md text-xs text-slate-400">
              Envía una consulta o selecciona una pregunta frecuente para recibir la
              respuesta del agente token por token.
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            {messages.map((msg) => {
              const isUser = msg.role === "user";
              const isInterrupted =
                msg.status === "interrupted" || Boolean(msg.interrupted);
              const isMsgStreaming = msg.status === "streaming";

              return (
                <div
                  key={msg.message_id || msg.id}
                  data-testid={`chat-msg-${msg.role}-${msg.status}`}
                  className={`flex flex-col gap-2 rounded-xl border p-4 transition-all ${
                    isUser
                      ? "ml-auto max-w-2xl border-indigo-200 bg-indigo-50/70 text-slate-900 dark:border-indigo-900/60 dark:bg-indigo-950/40 dark:text-slate-100"
                      : isInterrupted
                        ? "mr-auto max-w-3xl border-amber-300 bg-amber-50/60 text-slate-800 dark:border-amber-800/70 dark:bg-amber-950/30 dark:text-slate-200"
                        : "mr-auto max-w-3xl border-slate-200 bg-white text-slate-800 shadow-xs dark:border-slate-800 dark:bg-slate-900 dark:text-slate-200"
                  }`}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                        {isUser ? "Usuario (Soporte)" : "Agente TrackFlow"}
                      </span>
                      {msg.source_route && (
                        <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[10px] text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                          ruta: {msg.source_route}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-1.5">
                      {isMsgStreaming && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-indigo-100 px-2 py-0.5 text-[11px] font-semibold text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
                          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-indigo-600" />
                          Escribiendo...
                        </span>
                      )}
                      {isInterrupted && (
                        <span
                          data-testid="badge-interrupted"
                          className="inline-flex items-center gap-1 rounded-full bg-amber-200/80 px-2.5 py-0.5 text-[11px] font-semibold text-amber-900 dark:bg-amber-900/70 dark:text-amber-200"
                        >
                          Interrumpido (parcial conservado)
                        </span>
                      )}
                      {!isUser && msg.status === "completed" && (
                        <span className="inline-flex items-center rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-medium text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                          Completado
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="text-sm leading-relaxed whitespace-pre-wrap">
                    {msg.content}
                    {isMsgStreaming && (
                      <span
                        aria-hidden="true"
                        className="ml-0.5 inline-block h-4 w-1.5 animate-pulse bg-indigo-600 align-middle dark:bg-indigo-400"
                      />
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Error display */}
      {error && (
        <div
          id="rag-error-box"
          className="rounded-2xl border border-rose-200 bg-rose-50/70 p-5 text-sm text-rose-800 dark:border-rose-900/50 dark:bg-rose-950/30 dark:text-rose-300"
        >
          <div className="flex items-start gap-3">
            <svg
              className="mt-0.5 h-5 w-5 flex-shrink-0 text-rose-600 dark:text-rose-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <div>
              <p className="font-semibold">Aviso del canal de chat</p>
              <p className="mt-1 text-xs opacity-90">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Query & Mid-Stream Interruption Input Card */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSubmit();
          }}
          className="flex flex-col gap-4"
        >
          <div className="flex items-center justify-between">
            <label
              htmlFor="rag-question-input"
              className="text-sm font-medium text-slate-700 dark:text-slate-300"
            >
              {isStreaming
                ? "El agente está respondiendo — escribe aquí para interrumpir y redirigir el turno:"
                : "Escribe tu consulta:"}
            </label>
            {isStreaming && (
              <span className="text-xs font-medium text-amber-600 dark:text-amber-400">
                Puedes abortar o enviar un nuevo mensaje ahora mismo
              </span>
            )}
          </div>

          <div className="flex flex-col gap-3 sm:flex-row">
            <textarea
              id="rag-question-input"
              rows={3}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder={
                isStreaming
                  ? "Escribe una corrección o nueva instrucción para interrumpir al agente en caliente..."
                  : "Ej: ¿Cuál es el SLA comprometido mensualmente y qué compensación aplica si se incumple?"
              }
              className="flex-1 rounded-xl border border-slate-300 bg-slate-50/50 p-3.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-indigo-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 dark:border-slate-700 dark:bg-slate-800/60 dark:text-white dark:focus:bg-slate-800"
            />

            <div className="flex flex-col gap-2 sm:self-end">
              {isStreaming && (
                <button
                  id="ws-interrupt-btn"
                  type="button"
                  onClick={handleInterruptOnly}
                  className="inline-flex items-center justify-center gap-2 rounded-xl border border-amber-300 bg-amber-500 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-amber-600 dark:border-amber-700 dark:bg-amber-600 dark:hover:bg-amber-500"
                >
                  <svg
                    className="h-4 w-4"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <rect x="5" y="5" width="10" height="10" rx="1.5" />
                  </svg>
                  {question.trim() ? "Interrumpir y Redirigir" : "Interrumpir"}
                </button>
              )}

              <button
                id="rag-submit-btn"
                type="submit"
                disabled={!question.trim()}
                className="inline-flex items-center justify-center rounded-xl bg-indigo-600 px-6 py-3 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-indigo-500 dark:hover:bg-indigo-600"
              >
                {isStreaming ? "Enviar y Redirigir" : "Consultar"}
              </button>
            </div>
          </div>
        </form>

        {/* Suggested queries */}
        <div className="mt-6 border-t border-slate-100 pt-4 dark:border-slate-800">
          <p className="mb-2.5 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Consultas frecuentes recomendadas (clic para enviar o redirigir en vivo):
          </p>
          <div className="flex flex-wrap gap-2">
            {SUGGESTED_QUERIES.map((sq) => (
              <button
                key={sq.question}
                type="button"
                onClick={() => {
                  handleSubmit(sq.question);
                }}
                className="group inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:border-indigo-300 hover:bg-indigo-50/50 hover:text-indigo-700 dark:border-slate-700 dark:bg-slate-800/80 dark:text-slate-300 dark:hover:bg-indigo-950/40 dark:hover:text-indigo-300"
              >
                <span className="font-semibold text-slate-400 group-hover:text-indigo-500">
                  {sq.category}:
                </span>
                <span>{sq.question}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
