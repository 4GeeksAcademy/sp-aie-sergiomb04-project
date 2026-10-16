"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type ReadabilityMetrics = {
  flesch_kincaid_grade?: number;
  flesch_reading_ease?: number;
  gunning_fog?: number;
  coleman_liau?: number;
  dale_chall?: number;
  ari?: number;
  smog?: number;
  word_count?: number;
  sentence_count?: number;
};

type RFPMetadataPayload = {
  client_name?: string | null;
  client_country?: string | null;
  currency?: string | null;
  services_requested?: string[];
  monthly_volume?: number | null;
  deadline?: string | null;
  budget_range?: string | null;
  departments_needed?: string[];
};

type WorkerKeyAspects = {
  department_id?: string;
  department_name?: string;
  contact_person?: string;
  summary?: string;
  scope_items?: string[];
  constraints?: string[];
  resources_required?: string[];
  extracted_metrics?: Record<string, unknown>;
  open_questions?: string[];
  what_to_contribute?: string;
  relevant_excerpt?: string;
};

type DepartmentSectionRecord = {
  id: string;
  ticket_id: string;
  department_id: string;
  department: string;
  contact_person: string;
  key_aspects: WorkerKeyAspects;
  handoff_payload?: Record<string, unknown> | null;
  updated_at?: string | null;
};

type RFPTicketBundle = {
  ticket_id: string;
  rfp_id: string;
  status: "analizando" | "descartado" | "analisis_completo" | string;
  pdf_path: string;
  original_filename?: string | null;
  rejection_reason?: string | null;
  executive_summary?: string | null;
  handoff_payload?: Record<string, unknown> | null;
  metadata?: RFPMetadataPayload;
  readability_metrics?: ReadabilityMetrics;
  department_sections?: DepartmentSectionRecord[];
  created_at?: string | null;
  updated_at?: string | null;
};

type RFPTicketSummary = {
  ticket_id: string;
  rfp_id: string;
  status: string;
  original_filename?: string | null;
  client_name?: string | null;
  client_country?: string | null;
  currency?: string | null;
  departments_needed?: string[];
  created_at?: string | null;
};

const STATUS_BADGE_STYLES: Record<string, { label: string; className: string }> = {
  analizando: {
    label: "Analizando (Pipeline en curso)",
    className: "bg-amber-100 text-amber-800 border-amber-300",
  },
  analisis_completo: {
    label: "Análisis Completo (Listo para Ventas)",
    className: "bg-emerald-100 text-emerald-800 border-emerald-300",
  },
  descartado: {
    label: "Descartado (No es RFP válida)",
    className: "bg-rose-100 text-rose-800 border-rose-300",
  },
};

export default function RFPIntakePage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [activeTicketId, setActiveTicketId] = useState<string | null>(null);
  const [ticketDetail, setTicketDetail] = useState<RFPTicketBundle | null>(null);
  const [recentTickets, setRecentTickets] = useState<RFPTicketSummary[]>([]);
  const [polling, setPolling] = useState(false);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchRecentTickets = useCallback(async () => {
    try {
      const res = await fetch("/api/rfp", { cache: "no-store" });
      if (res.ok) {
        const list = (await res.json()) as RFPTicketSummary[];
        setRecentTickets(list);
      }
    } catch {
      // Ignore background list errors
    }
  }, []);

  const fetchTicketDetail = useCallback(
    async (ticketId: string) => {
      try {
        const res = await fetch(`/api/rfp/${encodeURIComponent(ticketId)}`, {
          cache: "no-store",
        });
        if (!res.ok) {
          return;
        }
        const data = (await res.json()) as RFPTicketBundle;
        setTicketDetail(data);

        if (data.status !== "analizando") {
          setPolling(false);
          if (pollTimerRef.current) {
            clearInterval(pollTimerRef.current);
            pollTimerRef.current = null;
          }
          fetchRecentTickets();
        }
      } catch {
        // Keep polling if transient network glitch
      }
    },
    [fetchRecentTickets]
  );

  useEffect(() => {
    const initTimer = setTimeout(() => {
      void fetchRecentTickets();
    }, 0);
    return () => {
      clearTimeout(initTimer);
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
      }
    };
  }, [fetchRecentTickets]);

  useEffect(() => {
    if (!activeTicketId) return;

    const initialFetchTimer = setTimeout(() => {
      void fetchTicketDetail(activeTicketId);
    }, 0);

    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
    }

    pollTimerRef.current = setInterval(() => {
      void fetchTicketDetail(activeTicketId);
    }, 1500);

    return () => {
      clearTimeout(initialFetchTimer);
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };
  }, [activeTicketId, fetchTicketDetail]);

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;

    setUploading(true);
    setUploadError(null);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      const res = await fetch("/api/rfp/upload", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errPayload = await res.json().catch(() => ({}));
        throw new Error(
          errPayload.detail || `Error al subir PDF (HTTP ${res.status})`
        );
      }

      const data = await res.json();
      setActiveTicketId(data.ticket_id);
      setPolling(true);
      setTicketDetail({
        ticket_id: data.ticket_id,
        rfp_id: data.rfp_id || "RFP-NEW",
        status: data.status || "analizando",
        pdf_path: data.pdf_path || `data/raw/${data.ticket_id}.pdf`,
        original_filename: selectedFile.name,
      });
      fetchRecentTickets();
    } catch (err) {
      setUploadError(
        err instanceof Error ? err.message : "Error inesperado al subir el PDF"
      );
    } finally {
      setUploading(false);
    }
  };

  const statusMeta = ticketDetail
    ? STATUS_BADGE_STYLES[ticketDetail.status] || {
        label: ticketDetail.status,
        className: "bg-slate-100 text-slate-800 border-slate-300",
      }
    : null;

  return (
    <div className="flex flex-1 flex-col gap-8 p-6 lg:p-10">
      {/* Header */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-3">
          <span className="rounded-md bg-indigo-50 px-2.5 py-1 text-xs font-semibold uppercase tracking-wider text-indigo-700">
            Hito 9 — Parte 1: RFP Intake & Routing
          </span>
          <span className="text-xs text-slate-500">
            Equipo Comercial: Miguel Torres
          </span>
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 lg:text-3xl">
          Recepción y Enrutamiento Agéntico de RFPs
        </h1>
        <p className="max-w-3xl text-sm text-slate-600">
          Sube documentos PDF de solicitudes de propuesta (formales o informales). El grafo
          LangGraph convierte el documento con MarkItDown, calcula métricas de legibilidad,
          clasifica su validez y descompone el análisis únicamente hacia los departamentos
          involucrados (Warehouse, Last Mile, Reverse Logistics).
        </p>
      </div>

      {/* Upload Form Card */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-base font-semibold text-slate-900">
          1. Subir Documento PDF de RFP
        </h2>
        <p className="mt-1 text-xs text-slate-500">
          Los archivos se almacenan en <code>data/raw/&lt;ticket_id&gt;.pdf</code> y disparan el
          pipeline asíncrono retornando HTTP 202 Accepted.
        </p>

        <form
          onSubmit={handleUploadSubmit}
          className="mt-4 flex flex-col gap-4 sm:flex-row sm:items-center"
        >
          <input
            id="rfp-pdf-input"
            type="file"
            accept=".pdf,application/pdf"
            onChange={(e) => {
              const f = e.target.files?.[0] ?? null;
              setSelectedFile(f);
              setUploadError(null);
            }}
            className="flex-1 rounded-xl border border-slate-300 bg-slate-50 px-3.5 py-2.5 text-sm text-slate-800 file:mr-4 file:rounded-lg file:border-0 file:bg-indigo-600 file:px-3.5 file:py-1.5 file:text-xs file:font-semibold file:text-white hover:file:bg-indigo-700"
          />
          <button
            id="rfp-upload-submit-btn"
            type="submit"
            disabled={!selectedFile || uploading}
            className="inline-flex items-center justify-center rounded-xl bg-indigo-600 px-6 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {uploading ? "Subiendo PDF..." : "Subir y Analizar RFP"}
          </button>
        </form>

        {uploadError && (
          <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-3.5 text-xs text-rose-800">
            <strong>Error:</strong> {uploadError}
          </div>
        )}

        {/* Recent Tickets Selector */}
        {recentTickets.length > 0 && (
          <div className="mt-5 border-t border-slate-100 pt-4">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
              Tickets RFP Recientes (clic para inspeccionar):
            </p>
            <div className="flex flex-wrap gap-2">
              {recentTickets.slice(0, 8).map((item) => (
                <button
                  key={item.ticket_id}
                  type="button"
                  onClick={() => {
                    setActiveTicketId(item.ticket_id);
                    setPolling(item.status === "analizando");
                  }}
                  className={[
                    "inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs font-medium transition",
                    activeTicketId === item.ticket_id
                      ? "border-indigo-500 bg-indigo-50 text-indigo-800"
                      : "border-slate-200 bg-slate-50 text-slate-700 hover:border-slate-300",
                  ].join(" ")}
                >
                  <span className="font-mono font-semibold">{item.rfp_id}</span>
                  <span>
                    {item.client_name || item.original_filename || item.ticket_id.slice(0, 8)}
                  </span>
                  <span
                    className={[
                      "rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase",
                      item.status === "analisis_completo"
                        ? "bg-emerald-100 text-emerald-700"
                        : item.status === "descartado"
                        ? "bg-rose-100 text-rose-700"
                        : "bg-amber-100 text-amber-700",
                    ].join(" ")}
                  >
                    {item.status}
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}
      </section>

      {/* Active Ticket Status & Results View */}
      {ticketDetail && (
        <div className="flex flex-col gap-6">
          {/* Status Header Banner */}
          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2.5">
                  <span className="font-mono text-sm font-bold text-indigo-700">
                    {ticketDetail.rfp_id}
                  </span>
                  <span className="text-xs text-slate-400">
                    ID: {ticketDetail.ticket_id}
                  </span>
                </div>
                <h2 className="mt-1 text-lg font-bold text-slate-900">
                  {ticketDetail.metadata?.client_name ||
                    ticketDetail.original_filename ||
                    "Documento RFP"}
                </h2>
                <p className="text-xs text-slate-500">
                  Archivo guardado en: <code>{ticketDetail.pdf_path}</code>
                </p>
              </div>

              {statusMeta && (
                <div className="flex items-center gap-2">
                  {polling && ticketDetail.status === "analizando" && (
                    <span className="h-3 w-3 animate-ping rounded-full bg-amber-500" />
                  )}
                  <span
                    id="rfp-ticket-status-badge"
                    className={`rounded-full border px-3.5 py-1.5 text-xs font-semibold ${statusMeta.className}`}
                  >
                    {statusMeta.label}
                  </span>
                </div>
              )}
            </div>

            {/* Discarded Notice */}
            {ticketDetail.status === "descartado" && (
              <div
                id="rfp-discarded-banner"
                className="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-900"
              >
                <p className="font-semibold">
                  Documento rechazado por el Agente Clasificador (Triage Agent)
                </p>
                <p className="mt-1 text-xs text-rose-800">
                  {ticketDetail.rejection_reason ||
                    "El documento no corresponde a una solicitud de propuesta (RFP) de cliente para TrackFlow."}
                </p>
              </div>
            )}
          </section>

          {/* Metadata & Readability Grid */}
          {ticketDetail.metadata && (
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              {/* Business Metadata */}
              <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">
                  Metadatos Extraídos de la RFP
                </h3>
                <dl className="mt-4 grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <dt className="text-xs text-slate-500">Cliente</dt>
                    <dd className="font-semibold text-slate-900">
                      {ticketDetail.metadata.client_name || "No especificado"}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-slate-500">País / Moneda Oficial</dt>
                    <dd className="font-semibold text-slate-900">
                      {ticketDetail.metadata.client_country || "N/D"} (
                      <span className="text-indigo-700">
                        {ticketDetail.metadata.currency || "N/D"}
                      </span>
                      )
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-slate-500">Volumen Mensual</dt>
                    <dd className="font-semibold text-slate-900">
                      {ticketDetail.metadata.monthly_volume != null
                        ? `${ticketDetail.metadata.monthly_volume.toLocaleString()} pedidos/mes`
                        : "No indicado (Pregunta abierta)"}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-slate-500">Fecha Límite (Deadline)</dt>
                    <dd className="font-semibold text-slate-900">
                      {ticketDetail.metadata.deadline || "No especificada"}
                    </dd>
                  </div>
                  <div className="col-span-2">
                    <dt className="text-xs text-slate-500">Presupuesto de Referencia</dt>
                    <dd className="font-semibold text-slate-900">
                      {ticketDetail.metadata.budget_range || "No especificado"}
                    </dd>
                  </div>
                  <div className="col-span-2">
                    <dt className="text-xs text-slate-500">
                      Departamentos Activados por el Orquestador
                    </dt>
                    <dd className="mt-1 flex flex-wrap gap-2">
                      {(ticketDetail.metadata.departments_needed ?? []).length > 0 ? (
                        ticketDetail.metadata.departments_needed?.map((dept) => (
                          <span
                            key={dept}
                            className="rounded-md bg-indigo-100 px-2.5 py-1 font-mono text-xs font-semibold text-indigo-800"
                          >
                            {dept}
                          </span>
                        ))
                      ) : (
                        <span className="text-xs text-slate-400">Ninguno</span>
                      )}
                    </dd>
                  </div>
                </dl>
              </section>

              {/* Readability Metrics */}
              <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">
                  Métricas de Legibilidad (py-readability-metrics)
                </h3>
                <div className="mt-4 grid grid-cols-3 gap-3 text-center">
                  <div className="rounded-xl bg-slate-50 p-3">
                    <p className="text-[11px] text-slate-500">Flesch-Kincaid Grade</p>
                    <p className="mt-1 text-lg font-bold text-slate-900">
                      {ticketDetail.readability_metrics?.flesch_kincaid_grade ?? "—"}
                    </p>
                  </div>
                  <div className="rounded-xl bg-slate-50 p-3">
                    <p className="text-[11px] text-slate-500">Gunning Fog</p>
                    <p className="mt-1 text-lg font-bold text-slate-900">
                      {ticketDetail.readability_metrics?.gunning_fog ?? "—"}
                    </p>
                  </div>
                  <div className="rounded-xl bg-slate-50 p-3">
                    <p className="text-[11px] text-slate-500">Flesch Reading Ease</p>
                    <p className="mt-1 text-lg font-bold text-slate-900">
                      {ticketDetail.readability_metrics?.flesch_reading_ease ?? "—"}
                    </p>
                  </div>
                  <div className="rounded-xl bg-slate-50 p-3">
                    <p className="text-[11px] text-slate-500">Coleman-Liau</p>
                    <p className="mt-1 text-base font-semibold text-slate-800">
                      {ticketDetail.readability_metrics?.coleman_liau ?? "—"}
                    </p>
                  </div>
                  <div className="rounded-xl bg-slate-50 p-3">
                    <p className="text-[11px] text-slate-500">Dale-Chall / SMOG</p>
                    <p className="mt-1 text-base font-semibold text-slate-800">
                      {ticketDetail.readability_metrics?.dale_chall ?? "—"} /{" "}
                      {ticketDetail.readability_metrics?.smog ?? "—"}
                    </p>
                  </div>
                  <div className="rounded-xl bg-slate-50 p-3">
                    <p className="text-[11px] text-slate-500">Palabras / Oraciones</p>
                    <p className="mt-1 text-base font-semibold text-slate-800">
                      {ticketDetail.readability_metrics?.word_count ?? 0} /{" "}
                      {ticketDetail.readability_metrics?.sentence_count ?? 0}
                    </p>
                  </div>
                </div>
              </section>
            </div>
          )}

          {/* Synthesizer Executive Summary for Sales */}
          {ticketDetail.executive_summary && (
            <section className="rounded-2xl border border-indigo-200 bg-indigo-50/40 p-6 shadow-sm">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-bold text-indigo-950">
                  Síntesis para Ventas (Synthesizer Agent): ¿Qué pedirle a qué departamento?
                </h3>
                {Boolean(ticketDetail.handoff_payload?.ready_for_part_2) && (
                  <span className="rounded-md bg-emerald-100 px-2.5 py-1 text-xs font-semibold text-emerald-800">
                    Handoff Contract Parte 2 Listo
                  </span>
                )}
              </div>
              <pre className="mt-3 whitespace-pre-wrap font-sans text-sm leading-relaxed text-slate-800">
                {ticketDetail.executive_summary}
              </pre>
            </section>
          )}

          {/* Breakdown of key_aspects per Department */}
          {ticketDetail.department_sections &&
            ticketDetail.department_sections.length > 0 && (
              <section className="flex flex-col gap-4">
                <h3 className="text-lg font-bold text-slate-900">
                  Desglose de Aspectos Clave por Departamento Activo (Workers Paralelos)
                </h3>
                <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
                  {ticketDetail.department_sections.map((sec) => {
                    const ka = sec.key_aspects || {};
                    return (
                      <div
                        key={sec.id}
                        className="flex flex-col justify-between rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
                      >
                        <div>
                          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                            <div>
                              <span className="rounded bg-slate-100 px-2 py-0.5 font-mono text-xs font-bold text-indigo-700">
                                {sec.department_id}
                              </span>
                              <h4 className="mt-1 text-base font-bold text-slate-900">
                                {sec.department}
                              </h4>
                            </div>
                            <div className="text-right">
                              <span className="text-[11px] text-slate-400">Responsable</span>
                              <p className="text-xs font-semibold text-slate-800">
                                {sec.contact_person}
                              </p>
                            </div>
                          </div>

                          <p className="mt-3 text-xs leading-relaxed text-slate-700">
                            {ka.summary}
                          </p>

                          {/* Scope Items */}
                          {ka.scope_items && ka.scope_items.length > 0 && (
                            <div className="mt-4">
                              <p className="text-xs font-semibold text-slate-900">
                                Alcance Operativo:
                              </p>
                              <ul className="mt-1 list-disc space-y-1 pl-4 text-xs text-slate-600">
                                {ka.scope_items.map((item, idx) => (
                                  <li key={idx}>{item}</li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {/* Constraints */}
                          {ka.constraints && ka.constraints.length > 0 && (
                            <div className="mt-4">
                              <p className="text-xs font-semibold text-slate-900">
                                Restricciones de Cumplimiento (§5):
                              </p>
                              <ul className="mt-1 list-disc space-y-1 pl-4 text-xs text-slate-600">
                                {ka.constraints.map((c, idx) => (
                                  <li key={idx}>{c}</li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {/* Open Questions */}
                          {ka.open_questions && ka.open_questions.length > 0 && (
                            <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-3">
                              <p className="text-xs font-semibold text-amber-900">
                                Preguntas Abiertas (Sin datos inventados):
                              </p>
                              <ul className="mt-1 list-disc space-y-1 pl-4 text-xs text-amber-800">
                                {ka.open_questions.map((q, idx) => (
                                  <li key={idx}>{q}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>

                        <div className="mt-4 border-t border-slate-100 pt-3 text-[11px] text-slate-500">
                          <strong>Entregable esperado:</strong> {ka.what_to_contribute}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>
            )}
        </div>
      )}
    </div>
  );
}
