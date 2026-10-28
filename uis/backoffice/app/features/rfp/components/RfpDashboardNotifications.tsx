"use client";

import Link from "next/link";
import { useState } from "react";
import { useRfpSseNotifications } from "../hooks/useRfpSseNotifications";

interface RfpDashboardNotificationsProps {
  initialToken?: string | null;
}

const DEPARTMENT_LABELS: Record<
  string,
  { name: string; lead: string; badgeClass: string }
> = {
  warehouse: {
    name: "Warehouse Operations",
    lead: "Ana Whitfield",
    badgeClass:
      "bg-indigo-100 text-indigo-800 border-indigo-300 dark:bg-indigo-950/70 dark:text-indigo-200 dark:border-indigo-700",
  },
  lastmile: {
    name: "Last Mile & Carriers",
    lead: "Carlos Vega",
    badgeClass:
      "bg-amber-100 text-amber-900 border-amber-300 dark:bg-amber-950/70 dark:text-amber-200 dark:border-amber-700",
  },
  reverse: {
    name: "Reverse Logistics",
    lead: "Sofía Ramos",
    badgeClass:
      "bg-emerald-100 text-emerald-900 border-emerald-300 dark:bg-emerald-950/70 dark:text-emerald-200 dark:border-emerald-700",
  },
};

const STATUS_STYLES: Record<string, { label: string; className: string }> = {
  analizando: {
    label: "Analizando",
    className:
      "bg-amber-100 text-amber-900 border-amber-300 dark:bg-amber-950/60 dark:text-amber-200 dark:border-amber-700",
  },
  analisis_completo: {
    label: "Análisis Completo",
    className:
      "bg-emerald-100 text-emerald-900 border-emerald-300 dark:bg-emerald-950/60 dark:text-emerald-200 dark:border-emerald-700",
  },
  descartado: {
    label: "Descartado",
    className:
      "bg-rose-100 text-rose-800 border-rose-300 dark:bg-rose-950/60 dark:text-rose-200 dark:border-rose-700",
  },
  generando_borrador: {
    label: "Generando Borrador",
    className:
      "bg-blue-100 text-blue-800 border-blue-300 dark:bg-blue-950/60 dark:text-blue-200 dark:border-blue-700",
  },
  en_evaluación: {
    label: "En Evaluación",
    className:
      "bg-purple-100 text-purple-800 border-purple-300 dark:bg-purple-950/60 dark:text-purple-200 dark:border-purple-700",
  },
  needs_human_review: {
    label: "Revisión Humana",
    className:
      "bg-orange-100 text-orange-900 border-orange-300 dark:bg-orange-950/60 dark:text-orange-200 dark:border-orange-700",
  },
  esperando_aprobación: {
    label: "Esperando Aprobación",
    className:
      "bg-orange-100 text-orange-900 border-orange-300 dark:bg-orange-950/60 dark:text-orange-200 dark:border-orange-700",
  },
  terminado: {
    label: "Terminado",
    className:
      "bg-emerald-100 text-emerald-900 border-emerald-400 dark:bg-emerald-950/70 dark:text-emerald-200 dark:border-emerald-600",
  },
};

export function RfpDashboardNotifications({
  initialToken = null,
}: RfpDashboardNotificationsProps) {
  const {
    tickets,
    latestLiveTicket,
    connectionState,
    retryAttempt,
    nextRetryDelayMs,
    lastEventId,
    errorMessage,
    dismissLatestAlert,
    manualReconnect,
  } = useRfpSseNotifications({ initialToken });

  const [creatingDemo, setCreatingDemo] = useState(false);

  const handleSimulateRfpTicket = async () => {
    setCreatingDemo(true);
    try {
      const sampleClients = [
        {
          client_name: "ModaViva",
          client_country: "Spain",
          currency: "EUR",
          services_requested: ["warehousing", "reverse_logistics"],
          monthly_volume: 12000,
          deadline: "2026-11-15",
          budget_range: "45,000 - 60,000 EUR/mes",
          departments_needed: ["warehouse", "reverse"],
          original_filename: "trackflow-request-1.pdf",
        },
        {
          client_name: "Luna Cosmetics",
          client_country: "USA",
          currency: "USD",
          services_requested: ["warehousing", "last_mile"],
          monthly_volume: 5000,
          deadline: "2026-11-30",
          budget_range: "28,000 - 35,000 USD/month",
          departments_needed: ["warehouse", "lastmile"],
          original_filename: "trackflow-request-2.pdf",
        },
      ];
      const pick = sampleClients[tickets.length % sampleClients.length];
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (initialToken) {
        headers.Authorization = `Bearer ${initialToken}`;
      }
      await fetch("/api/rfp", {
        method: "POST",
        headers,
        body: JSON.stringify(pick),
      });
    } finally {
      setCreatingDemo(false);
    }
  };

  return (
    <section
      id="rfp-sse-notifications-panel"
      aria-label="Notificaciones de Tickets RFP en Tiempo Real (SSE)"
      className="relative overflow-hidden rounded-2xl border-2 border-indigo-500/80 bg-gradient-to-br from-indigo-50/90 via-white to-amber-50/50 p-6 shadow-md dark:border-indigo-500/70 dark:from-indigo-950/60 dark:via-slate-900 dark:to-amber-950/20"
    >
      {/* Top accent bar to visually distinguish RFP notifications from standard dashboard cards */}
      <div className="flex flex-col justify-between gap-4 border-b border-indigo-200/70 pb-4 lg:flex-row lg:items-center dark:border-indigo-800/60">
        <div className="flex items-start gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-indigo-600 text-lg font-bold text-white shadow-sm dark:bg-indigo-500">
            🔔
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full bg-indigo-600 px-2.5 py-0.5 text-xs font-bold uppercase tracking-wider text-white dark:bg-indigo-500">
                Canal Tiempo Real · SSE
              </span>
              <span className="font-mono text-xs font-semibold text-indigo-800 dark:text-indigo-300">
                event: rfp_ticket_created
              </span>
              {connectionState === "connected" && (
                <span
                  id="rfp-sse-connection-badge"
                  className="inline-flex items-center gap-1.5 rounded-full border border-emerald-300 bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-800 dark:border-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300"
                >
                  <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-500" />
                  Stream Activo (fetch + ReadableStream)
                </span>
              )}
              {connectionState === "connecting" && (
                <span
                  id="rfp-sse-connection-badge"
                  className="inline-flex items-center gap-1.5 rounded-full border border-blue-300 bg-blue-50 px-2.5 py-0.5 text-xs font-semibold text-blue-800 dark:border-blue-700 dark:bg-blue-950/60 dark:text-blue-300"
                >
                  <span className="h-2 w-2 animate-ping rounded-full bg-blue-500" />
                  Conectando SSE...
                </span>
              )}
              {connectionState === "reconnecting" && (
                <span
                  id="rfp-sse-connection-badge"
                  className="inline-flex items-center gap-1.5 rounded-full border border-amber-300 bg-amber-50 px-2.5 py-0.5 text-xs font-semibold text-amber-900 dark:border-amber-700 dark:bg-amber-950/60 dark:text-amber-200"
                >
                  <span className="h-2 w-2 animate-ping rounded-full bg-amber-500" />
                  Reconectando (Intento #{retryAttempt} · Backoff{" "}
                  {nextRetryDelayMs ? `${Math.round(nextRetryDelayMs / 1000)}s` : ""})
                </span>
              )}
              {connectionState === "error" && (
                <span
                  id="rfp-sse-connection-badge"
                  className="inline-flex items-center gap-1.5 rounded-full border border-rose-300 bg-rose-50 px-2.5 py-0.5 text-xs font-semibold text-rose-800 dark:border-rose-700 dark:bg-rose-950/60 dark:text-rose-300"
                >
                  Desconectado
                </span>
              )}
            </div>
            <h2 className="mt-1.5 text-xl font-bold tracking-tight text-slate-950 dark:text-white">
              Alertas Comerciales de Nuevos Tickets de RFP (Miguel Torres)
            </h2>
            <p className="text-xs text-slate-600 dark:text-slate-300">
              Recepción instantánea sin recargar la página con autenticación JWT en cabeceras,
              reconexión con backoff progresivo y deduplicación automática vía{" "}
              <code className="rounded bg-indigo-100/80 px-1 py-0.5 font-mono text-[11px] text-indigo-900 dark:bg-indigo-950 dark:text-indigo-200">
                Last-Event-ID
              </code>
              {lastEventId ? ` (${lastEventId})` : ""}.
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            id="simulate-rfp-sse-btn"
            type="button"
            onClick={() => void handleSimulateRfpTicket()}
            disabled={creatingDemo}
            className="rounded-xl bg-indigo-600 px-3.5 py-2 text-xs font-bold text-white shadow-sm transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {creatingDemo ? "Registrando..." : "+ Registrar Ticket RFP (Test SSE)"}
          </button>
          <Link
            href="/rfp"
            prefetch={false}
            className="rounded-xl border border-indigo-300 bg-white px-3.5 py-2 text-xs font-semibold text-indigo-700 shadow-xs transition hover:bg-indigo-50 dark:border-indigo-700 dark:bg-slate-800 dark:text-indigo-200 dark:hover:bg-slate-700"
          >
            Ir a RFP Intake →
          </Link>
          {connectionState !== "connected" && (
            <button
              type="button"
              onClick={manualReconnect}
              className="rounded-xl border border-amber-300 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-900 hover:bg-amber-100 dark:border-amber-700 dark:bg-amber-950/60 dark:text-amber-200"
            >
              Reconectar ahora
            </button>
          )}
        </div>
      </div>

      {errorMessage && connectionState === "reconnecting" && (
        <div
          role="status"
          className="mt-3 rounded-xl border border-amber-300 bg-amber-50/90 px-4 py-2.5 text-xs text-amber-900 dark:border-amber-800 dark:bg-amber-950/50 dark:text-amber-200"
        >
          <span className="font-bold">Recuperación automática activa:</span> {errorMessage}. Reintentando en{" "}
          {nextRetryDelayMs ? `${(nextRetryDelayMs / 1000).toFixed(0)}s` : "breve"} con{" "}
          <code>Last-Event-ID</code> y deduplicación de eventos.
        </div>
      )}

      {/* High-visibility banner when a live SSE rfp_ticket_created notification arrives */}
      {latestLiveTicket && (
        <div
          id="rfp-live-notification-banner"
          role="alert"
          className="mt-4 flex flex-col justify-between gap-3 rounded-xl border-2 border-amber-400 bg-amber-50/95 p-4 shadow-sm sm:flex-row sm:items-center dark:border-amber-500/80 dark:bg-amber-950/60"
        >
          <div className="flex items-start gap-3">
            <span className="mt-0.5 rounded-lg bg-amber-500 px-2 py-1 text-[11px] font-extrabold uppercase tracking-wider text-white">
              NUEVA RFP EN VIVO
            </span>
            <div>
              <p className="text-sm font-bold text-slate-950 dark:text-white">
                Ticket <span className="font-mono text-indigo-700 dark:text-indigo-300">{latestLiveTicket.rfp_id}</span>{" "}
                registrado para{" "}
                <span className="underline decoration-amber-500/70">
                  {latestLiveTicket.client_name || latestLiveTicket.original_filename || "Cliente E-Commerce"}
                </span>{" "}
                {latestLiveTicket.client_country ? `(${latestLiveTicket.client_country} · ${latestLiveTicket.currency || "N/D"})` : ""}
              </p>
              <p className="mt-0.5 text-xs text-slate-700 dark:text-slate-300">
                Estado: <strong>{latestLiveTicket.status}</strong> · Archivo:{" "}
                <code className="font-mono">{latestLiveTicket.raw_pdf_path}</code>
                {latestLiveTicket.departments_needed && latestLiveTicket.departments_needed.length > 0 && (
                  <>
                    {" "}
                    · Departamentos activados:{" "}
                    <strong>{latestLiveTicket.departments_needed.join(", ")}</strong>
                  </>
                )}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={dismissLatestAlert}
            className="self-end rounded-lg border border-amber-300 bg-white px-2.5 py-1 text-xs font-semibold text-amber-900 hover:bg-amber-100 sm:self-center dark:border-amber-700 dark:bg-slate-800 dark:text-amber-200"
          >
            Entendido
          </button>
        </div>
      )}

      {/* Deduplicated list of RFP Ticket notifications */}
      <div className="mt-4">
        {tickets.length === 0 ? (
          <div className="rounded-xl border border-dashed border-indigo-200 bg-white/80 p-6 text-center dark:border-indigo-900/60 dark:bg-slate-900/60">
            <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
              Esperando nuevos eventos <code className="font-mono text-indigo-600 dark:text-indigo-400">rfp_ticket_created</code> en tiempo real...
            </p>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              Cuando se suba o registre una RFP en el sistema, aparecerá instantáneamente aquí sin recargar el dashboard.
            </p>
          </div>
        ) : (
          <div className="grid gap-3 md:grid-cols-2">
            {tickets.slice(0, 6).map((ticket) => {
              const statusBadge = STATUS_STYLES[ticket.status] || {
                label: ticket.status,
                className:
                  "bg-slate-100 text-slate-800 border-slate-300 dark:bg-slate-800 dark:text-slate-200 dark:border-slate-700",
              };
              const depts = ticket.departments_needed ?? [];

              return (
                <article
                  key={ticket.ticket_id}
                  data-testid={`rfp-notification-card-${ticket.ticket_id}`}
                  className={`flex flex-col justify-between rounded-xl border p-4 transition ${
                    ticket.isLiveNotification
                      ? "border-indigo-400 bg-indigo-50/70 ring-2 ring-indigo-400/40 dark:border-indigo-500 dark:bg-indigo-950/50"
                      : "border-indigo-200/80 bg-white/95 dark:border-slate-800 dark:bg-slate-900/90"
                  }`}
                >
                  <div>
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="rounded-md bg-indigo-900 px-2 py-0.5 font-mono text-xs font-bold text-white dark:bg-indigo-600">
                          {ticket.rfp_id}
                        </span>
                        {ticket.isLiveNotification && (
                          <span className="rounded-full bg-amber-400/90 px-2 py-0.5 text-[10px] font-extrabold uppercase tracking-wider text-slate-950">
                            SSE EN VIVO
                          </span>
                        )}
                      </div>
                      <span
                        className={`rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${statusBadge.className}`}
                      >
                        {statusBadge.label}
                      </span>
                    </div>

                    <h3 className="mt-2 text-base font-bold text-slate-950 dark:text-white">
                      {ticket.client_name || ticket.original_filename || "Solicitud RFP"}
                      {ticket.client_country && (
                        <span className="ml-2 text-xs font-semibold text-indigo-700 dark:text-indigo-300">
                          · {ticket.client_country} ({ticket.currency || "USD/EUR"})
                        </span>
                      )}
                    </h3>

                    <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-xs text-slate-600 dark:text-slate-300">
                      <div>
                        <span className="font-medium text-slate-500 dark:text-slate-400">Volumen:</span>{" "}
                        {ticket.monthly_volume != null
                          ? `${ticket.monthly_volume.toLocaleString()} pedidos/mes`
                          : "Por confirmar"}
                      </div>
                      <div>
                        <span className="font-medium text-slate-500 dark:text-slate-400">Deadline:</span>{" "}
                        {ticket.deadline || "N/D"}
                      </div>
                      {ticket.budget_range && (
                        <div className="col-span-2">
                          <span className="font-medium text-slate-500 dark:text-slate-400">Presupuesto:</span>{" "}
                          {ticket.budget_range}
                        </div>
                      )}
                    </div>

                    {depts.length > 0 && (
                      <div className="mt-3 flex flex-wrap gap-1.5">
                        {depts.map((deptId) => {
                          const deptMeta = DEPARTMENT_LABELS[deptId];
                          return (
                            <span
                              key={deptId}
                              className={`rounded-md border px-2 py-0.5 text-[11px] font-semibold ${
                                deptMeta?.badgeClass ||
                                "border-slate-300 bg-slate-100 text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
                              }`}
                            >
                              {deptId}
                              {deptMeta ? ` · ${deptMeta.lead}` : ""}
                            </span>
                          );
                        })}
                      </div>
                    )}
                  </div>

                  <div className="mt-3 flex items-center justify-between border-t border-slate-100 pt-2 text-[11px] text-slate-400 dark:border-slate-800 dark:text-slate-500">
                    <span className="truncate font-mono">
                      ID: {ticket.ticket_id.slice(0, 8)}… · {ticket.raw_pdf_path}
                    </span>
                    <span className="shrink-0">
                      {ticket.created_at
                        ? new Date(ticket.created_at).toLocaleTimeString()
                        : ""}
                    </span>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}
