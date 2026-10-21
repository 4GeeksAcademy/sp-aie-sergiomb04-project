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

type EvaluationResultPayload = {
  department_id: string;
  section_id?: string | null;
  readability: {
    pass: boolean;
    score: number;
    details: Record<string, unknown> | string;
  };
  relevance: {
    pass: boolean;
    missing_aspects: string[];
  };
  compliance: {
    pass: boolean;
    rule_ids: string[];
    violations: string[];
  };
  overall_pass: boolean;
  feedback_for_generator: string;
};

type DepartmentSectionRecord = {
  id: string;
  ticket_id: string;
  department_id: string;
  department: string;
  contact_person: string;
  key_aspects: WorkerKeyAspects;
  handoff_payload?: Record<string, unknown> | null;
  draft_content?: string | null;
  evaluation_results?: EvaluationResultPayload | null;
  approval_status?: string | null;
  updated_at?: string | null;
};

type RFPTicketBundle = {
  ticket_id: string;
  rfp_id: string;
  status:
    | "analizando"
    | "descartado"
    | "analisis_completo"
    | "generando_borrador"
    | "en_evaluación"
    | "needs_human_review"
    | string;
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
  generando_borrador: {
    label: "Generando Borrador (Redacción en curso)",
    className: "bg-blue-100 text-blue-800 border-blue-300",
  },
  en_evaluación: {
    label: "En Evaluación (Evaluadores paralelos)",
    className: "bg-purple-100 text-purple-800 border-purple-300",
  },
  needs_human_review: {
    label: "Revisión Humana Requerida (Límite agotado)",
    className: "bg-amber-100 text-amber-900 border-amber-400 font-bold",
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
  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);
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

        // Keep polling during active async steps
        const isStillRunning =
          data.status === "analizando" ||
          data.status === "generando_borrador" ||
          (data.status === "en_evaluación" &&
            data.department_sections?.some((sec) => !sec.draft_content));

        if (!isStillRunning) {
          setPolling(false);
          setGenerating(false);
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

      const data = (await res.json()) as { ticket_id: string };
      setActiveTicketId(data.ticket_id);
      setSelectedFile(null);
      setPolling(true);
      void fetchRecentTickets();
    } catch (err) {
      setUploadError(
        err instanceof Error ? err.message : "Error inesperado al subir archivo"
      );
    } finally {
      setUploading(false);
    }
  };

  const handleTriggerGeneration = async () => {
    if (!ticketDetail) return;
    setGenerating(true);
    setGenerateError(null);

    try {
      const res = await fetch(`/api/rfp/${encodeURIComponent(ticketDetail.ticket_id)}/generate`, {
        method: "POST",
      });

      if (!res.ok) {
        const errPayload = await res.json().catch(() => ({}));
        throw new Error(
          errPayload.detail || `Error al iniciar generación (HTTP ${res.status})`
        );
      }

      setPolling(true);
      void fetchTicketDetail(ticketDetail.ticket_id);
      void fetchRecentTickets();
    } catch (err) {
      setGenerateError(
        err instanceof Error ? err.message : "Error al iniciar la propuesta"
      );
      setGenerating(false);
    }
  };

  const statusMeta = ticketDetail
    ? STATUS_BADGE_STYLES[ticketDetail.status] || {
        label: ticketDetail.status,
        className: "bg-slate-100 text-slate-800 border-slate-300",
      }
    : null;

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-8 p-6">
      {/* Header */}
      <div>
        <span className="rounded bg-indigo-50 px-2.5 py-1 text-xs font-semibold uppercase tracking-wider text-indigo-700">
          TrackFlow Tech · Hito 9
        </span>
        <h1 className="mt-2 text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
          Flujo Agéntico de RFPs: Recepción, Enrutamiento y Generación de Respuestas
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Recepción automatizada, triage con clasificador, extracción con MarkItDown,
          generación de borradores y ciclo de evaluación paralela de legibilidad, pertinencia y cumplimiento (§5).
        </p>
      </div>

      {/* Main Grid: Upload + Recent Tickets */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Upload Form Card */}
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-600 text-xs font-bold text-white">
              1
            </span>
            <h2 className="text-base font-bold text-slate-900">
              Subida de RFP en PDF (Modo Ticket)
            </h2>
          </div>
          <p className="mt-2 text-xs text-slate-500">
            Sube la solicitud recibida. Se guardará en <code>data/raw/</code> y creará un ticket en PostgreSQL.
          </p>

          <form onSubmit={handleUploadSubmit} className="mt-4 flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <label
                htmlFor="rfp-file-input"
                className="text-xs font-medium text-slate-700"
              >
                Archivo RFP (.pdf)
              </label>
              <input
                id="rfp-file-input"
                type="file"
                accept=".pdf,application/pdf"
                onChange={(e) => {
                  const file = e.target.files?.[0] || null;
                  setSelectedFile(file);
                  setUploadError(null);
                }}
                className="block w-full cursor-pointer rounded-xl border border-slate-300 bg-slate-50/50 px-3 py-2 text-xs text-slate-800 file:mr-3 file:rounded-lg file:border-0 file:bg-indigo-50 file:px-3 file:py-1.5 file:text-xs file:font-semibold file:text-indigo-700 hover:file:bg-indigo-100"
              />
            </div>

            {selectedFile && (
              <div className="rounded-lg bg-slate-50 p-2.5 text-xs text-slate-600">
                <span className="font-semibold text-slate-800">Seleccionado:</span>{" "}
                {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
              </div>
            )}

            {uploadError && (
              <div
                id="rfp-upload-error"
                className="rounded-lg border border-rose-200 bg-rose-50 p-2.5 text-xs text-rose-700"
              >
                {uploadError}
              </div>
            )}

            <button
              id="rfp-upload-submit-btn"
              type="submit"
              disabled={!selectedFile || uploading}
              className="flex items-center justify-center rounded-xl bg-indigo-600 px-4 py-2.5 text-xs font-semibold text-white shadow-sm transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              {uploading ? (
                <>
                  <span className="mr-2 h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  Subiendo y encolando...
                </>
              ) : (
                "Subir RFP e Iniciar Análisis"
              )}
            </button>
          </form>
        </section>

        {/* Recent Tickets List */}
        <section className="col-span-1 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm lg:col-span-2">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h2 className="text-base font-bold text-slate-900">
              Historial de Tickets RFP en PostgreSQL
            </h2>
            <button
              onClick={() => void fetchRecentTickets()}
              className="rounded-lg px-2.5 py-1 text-xs font-medium text-indigo-600 hover:bg-indigo-50"
            >
              Refrescar lista
            </button>
          </div>

          <div className="mt-3 max-h-64 overflow-y-auto">
            {recentTickets.length === 0 ? (
              <p className="py-6 text-center text-xs text-slate-400">
                No hay tickets registrados aún. Sube un PDF para comenzar.
              </p>
            ) : (
              <div className="divide-y divide-slate-100">
                {recentTickets.map((t) => {
                  const badge = STATUS_BADGE_STYLES[t.status] || {
                    label: t.status,
                    className: "bg-slate-100 text-slate-700 border-slate-200",
                  };
                  const isSelected = activeTicketId === t.ticket_id;
                  return (
                    <div
                      key={t.ticket_id}
                      onClick={() => setActiveTicketId(t.ticket_id)}
                      className={`flex cursor-pointer items-center justify-between p-3 text-xs transition hover:bg-slate-50 ${
                        isSelected ? "bg-indigo-50/60 font-semibold" : ""
                      }`}
                    >
                      <div className="flex flex-col gap-0.5">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-bold text-indigo-900">
                            {t.rfp_id}
                          </span>
                          <span className="text-slate-700">
                            {t.client_name || t.original_filename || "Sin nombre"}
                          </span>
                          {t.client_country && (
                            <span className="text-slate-400">
                              ({t.client_country})
                            </span>
                          )}
                        </div>
                        <span className="text-[11px] text-slate-400">
                          {t.created_at ? new Date(t.created_at).toLocaleString() : ""}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span
                          className={`rounded-full border px-2.5 py-0.5 text-[11px] font-medium ${badge.className}`}
                        >
                          {badge.label}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </section>
      </div>

      {/* Ticket Details View */}
      {ticketDetail && (
        <div id="rfp-ticket-detail-view" className="flex flex-col gap-6">
          {/* Ticket Header & Status Banner */}
          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
              <div>
                <div className="flex items-center gap-2">
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

              <div className="flex flex-wrap items-center gap-3">
                {polling && (
                  <div className="flex items-center gap-1.5 text-xs text-indigo-600">
                    <span className="h-2.5 w-2.5 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent" />
                    <span>Actualizando en tiempo real...</span>
                  </div>
                )}
                {statusMeta && (
                  <span
                    id="rfp-ticket-status-badge"
                    className={`rounded-full border px-3.5 py-1.5 text-xs font-semibold ${statusMeta.className}`}
                  >
                    {statusMeta.label}
                  </span>
                )}
                {/* Generation Trigger Button */}
                {(ticketDetail.status === "analisis_completo" ||
                  ticketDetail.status === "en_evaluación" ||
                  ticketDetail.status === "needs_human_review") && (
                  <button
                    id="trigger-generate-btn"
                    onClick={() => void handleTriggerGeneration()}
                    disabled={generating || polling}
                    className="flex items-center gap-1.5 rounded-xl bg-emerald-600 px-4 py-2 text-xs font-bold text-white shadow hover:bg-emerald-500 disabled:cursor-not-allowed disabled:bg-slate-300"
                  >
                    {generating ? (
                      <>
                        <span className="h-3 w-3 animate-spin rounded-full border-2 border-white border-t-transparent" />
                        Generando y Evaluando...
                      </>
                    ) : (
                      <>⚡ Generar Propuesta Económica por Departamentos</>
                    )}
                  </button>
                )}
              </div>
            </div>

            {generateError && (
              <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800">
                {generateError}
              </div>
            )}

            {/* Needs Human Review Warning Banner */}
            {ticketDetail.status === "needs_human_review" && (
              <div
                id="rfp-needs-human-review-banner"
                className="mt-4 rounded-xl border-2 border-amber-300 bg-amber-50 p-4 text-xs text-amber-900 shadow-sm"
              >
                <div className="flex items-center gap-2">
                  <span className="rounded bg-amber-200 px-2 py-0.5 font-bold text-amber-900">
                    ⚠️ ACCIÓN REQUERIDA
                  </span>
                  <p className="font-bold text-amber-950">
                    Revisión Humana Requerida — Límite de Iteraciones Agotado
                  </p>
                </div>
                <p className="mt-1.5 leading-relaxed text-amber-900">
                  Una o más secciones generadas han agotado el límite de reintentos del ciclo generador-evaluador sin superar la totalidad de los criterios automatizados.
                  El último borrador generado se ha conservado como <strong>provisional</strong> junto a su reporte de evaluación para que el equipo comercial de Miguel Torres realice los ajustes correspondientes antes del paso a aprobación final. El ticket <strong>no ha sido descartado</strong>.
                </p>
              </div>
            )}

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
                            className="rounded-md bg-indigo-100 px-2.5 py-1 text-xs font-semibold text-indigo-800"
                          >
                            {dept}
                          </span>
                        ))
                      ) : (
                        <span className="text-xs italic text-slate-400">
                          Ninguno detectado
                        </span>
                      )}
                    </dd>
                  </div>
                </dl>
              </section>

              {/* Readability Metrics Card */}
              <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                  <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">
                    Métricas de Legibilidad (py-readability-metrics)
                  </h3>
                  <span className="text-[11px] text-slate-400">Estimación de coste</span>
                </div>
                <div className="mt-4 grid grid-cols-2 gap-4 text-xs sm:grid-cols-3">
                  <div className="rounded-xl bg-slate-50 p-3">
                    <p className="text-[11px] text-slate-500">Flesch Reading Ease</p>
                    <p className="mt-1 text-base font-semibold text-slate-800">
                      {ticketDetail.readability_metrics?.flesch_reading_ease ?? "N/D"}
                    </p>
                  </div>
                  <div className="rounded-xl bg-slate-50 p-3">
                    <p className="text-[11px] text-slate-500">Flesch-Kincaid Grade</p>
                    <p className="mt-1 text-base font-semibold text-slate-800">
                      {ticketDetail.readability_metrics?.flesch_kincaid_grade ?? "N/D"}
                    </p>
                  </div>
                  <div className="rounded-xl bg-slate-50 p-3">
                    <p className="text-[11px] text-slate-500">Gunning Fog Index</p>
                    <p className="mt-1 text-base font-semibold text-slate-800">
                      {ticketDetail.readability_metrics?.gunning_fog ?? "N/D"}
                    </p>
                  </div>
                  <div className="rounded-xl bg-slate-50 p-3">
                    <p className="text-[11px] text-slate-500">Coleman-Liau</p>
                    <p className="mt-1 text-base font-semibold text-slate-800">
                      {ticketDetail.readability_metrics?.coleman_liau ?? "N/D"}
                    </p>
                  </div>
                  <div className="rounded-xl bg-slate-50 p-3">
                    <p className="text-[11px] text-slate-500">SMOG Score</p>
                    <p className="mt-1 text-base font-semibold text-slate-800">
                      {ticketDetail.readability_metrics?.smog ?? "N/D"}
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

          {/* Department Breakdown & Generated Drafts (Milestone 9 - Part 2) */}
          {ticketDetail.department_sections &&
            ticketDetail.department_sections.length > 0 && (
              <section className="flex flex-col gap-6">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-bold text-slate-900">
                    Propuestas Económicas por Departamento y Evaluación Paralela
                  </h3>
                  <span className="text-xs text-slate-500">
                    Generador individual por departamento · Evaluadores en paralelo
                  </span>
                </div>

                <div className="grid grid-cols-1 gap-6">
                  {ticketDetail.department_sections.map((sec) => {
                    const ka = sec.key_aspects || {};
                    const ev = sec.evaluation_results;
                    const isDraftReady = Boolean(sec.draft_content);
                    const isNeedsReview = sec.approval_status === "needs_human_review";

                    return (
                      <div
                        key={sec.id}
                        className={`flex flex-col rounded-2xl border bg-white p-6 shadow-sm ${
                          isNeedsReview
                            ? "border-amber-300 ring-2 ring-amber-200"
                            : "border-slate-200"
                        }`}
                      >
                        {/* Section Header */}
                        <div className="flex flex-col justify-between gap-2 border-b border-slate-100 pb-4 sm:flex-row sm:items-center">
                          <div className="flex items-center gap-3">
                            <span className="rounded-lg bg-indigo-100 px-2.5 py-1 font-mono text-xs font-bold text-indigo-800">
                              {sec.department_id}
                            </span>
                            <div>
                              <h4 className="text-base font-bold text-slate-900">
                                {sec.department}
                              </h4>
                              <p className="text-xs text-slate-500">
                                Responsable: <strong>{sec.contact_person}</strong>
                              </p>
                            </div>
                          </div>

                          <div className="flex items-center gap-2">
                            {isNeedsReview && (
                              <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-bold text-amber-800 border border-amber-300">
                                ⚠️ Requiere Revisión Humana
                              </span>
                            )}
                            {ev && ev.overall_pass && (
                              <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-800 border border-emerald-300">
                                Evaluación Aprobada ✅
                              </span>
                            )}
                            {!isDraftReady && (
                              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
                                Pendiente de Generación
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Analysis Key Aspects (Part 1 input) */}
                        <div className="mt-4 rounded-xl bg-slate-50/80 p-4 text-xs text-slate-700">
                          <p className="font-semibold text-slate-900">
                            Resumen de Requerimientos Iniciales (Handoff Parte 1):
                          </p>
                          <p className="mt-1 leading-relaxed">{ka.summary}</p>
                          {ka.open_questions && ka.open_questions.length > 0 && (
                            <div className="mt-2 text-[11px] text-amber-800">
                              <strong>Preguntas abiertas pendientes:</strong>{" "}
                              {ka.open_questions.join("; ")}
                            </div>
                          )}
                        </div>

                        {/* Generated Draft Section */}
                        {isDraftReady && (
                          <div className="mt-6 flex flex-col gap-4">
                            <div className="flex items-center justify-between">
                              <h5 className="text-sm font-bold text-slate-900">
                                Borrador de la Propuesta Económica Generado
                              </h5>
                              {isNeedsReview && (
                                <span className="text-xs italic text-amber-700">
                                  (Borrador provisional conservado tras agotar iteraciones)
                                </span>
                              )}
                            </div>
                            <div className="rounded-xl border border-slate-200 bg-slate-900/5 p-4 font-mono text-xs text-slate-800 whitespace-pre-wrap leading-relaxed max-h-96 overflow-y-auto">
                              {sec.draft_content}
                            </div>
                          </div>
                        )}

                        {/* Parallel Evaluation Results (Part 2) */}
                        {ev && (
                          <div className="mt-6 border-t border-slate-100 pt-5">
                            <h5 className="text-sm font-bold text-slate-900">
                              Resultado de la Evaluación Automatizada en Paralelo (EvaluationResult)
                            </h5>

                            <div className="mt-3 grid grid-cols-1 gap-4 md:grid-cols-3">
                              {/* Readability Card */}
                              <div
                                className={`rounded-xl border p-3.5 text-xs ${
                                  ev.readability?.pass
                                    ? "border-emerald-200 bg-emerald-50/40"
                                    : "border-rose-200 bg-rose-50/40"
                                }`}
                              >
                                <div className="flex items-center justify-between">
                                  <span className="font-bold text-slate-800">
                                    Legibilidad
                                  </span>
                                  <span
                                    className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                                      ev.readability?.pass
                                        ? "bg-emerald-200 text-emerald-900"
                                        : "bg-rose-200 text-rose-900"
                                    }`}
                                  >
                                    {ev.readability?.pass ? "APROBADO" : "FALLO"}
                                  </span>
                                </div>
                                <p className="mt-2 text-[11px] text-slate-600">
                                  Score Reading Ease:{" "}
                                  <strong>{ev.readability?.score ?? "N/D"}</strong>
                                </p>
                              </div>

                              {/* Relevance Card */}
                              <div
                                className={`rounded-xl border p-3.5 text-xs ${
                                  ev.relevance?.pass
                                    ? "border-emerald-200 bg-emerald-50/40"
                                    : "border-rose-200 bg-rose-50/40"
                                }`}
                              >
                                <div className="flex items-center justify-between">
                                  <span className="font-bold text-slate-800">
                                    Pertinencia
                                  </span>
                                  <span
                                    className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                                      ev.relevance?.pass
                                        ? "bg-emerald-200 text-emerald-900"
                                        : "bg-rose-200 text-rose-900"
                                    }`}
                                  >
                                    {ev.relevance?.pass ? "APROBADO" : "FALLO"}
                                  </span>
                                </div>
                                <p className="mt-2 text-[11px] text-slate-600">
                                  {ev.relevance?.missing_aspects?.length === 0
                                    ? "Cubre todos los aspectos requeridos."
                                    : `Faltan ${ev.relevance?.missing_aspects?.length} aspectos.`}
                                </p>
                              </div>

                              {/* Compliance Card */}
                              <div
                                className={`rounded-xl border p-3.5 text-xs ${
                                  ev.compliance?.pass
                                    ? "border-emerald-200 bg-emerald-50/40"
                                    : "border-rose-200 bg-rose-50/40"
                                }`}
                              >
                                <div className="flex items-center justify-between">
                                  <span className="font-bold text-slate-800">
                                    Lineamientos (§5)
                                  </span>
                                  <span
                                    className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                                      ev.compliance?.pass
                                        ? "bg-emerald-200 text-emerald-900"
                                        : "bg-rose-200 text-rose-900"
                                    }`}
                                  >
                                    {ev.compliance?.pass ? "CUMPLE 5/5" : "INFRACCIÓN"}
                                  </span>
                                </div>
                                <p className="mt-2 text-[11px] text-slate-600">
                                  {ev.compliance?.violations?.length === 0
                                    ? "Moneda, SLA, devoluciones y descuentos validados."
                                    : `${ev.compliance?.violations?.length} infracciones detectadas.`}
                                </p>
                              </div>
                            </div>

                            {/* Detailed Feedback & Violations */}
                            {ev.feedback_for_generator && (
                              <div className="mt-3 rounded-xl border border-slate-200 bg-slate-50 p-3.5 text-xs">
                                <p className="font-semibold text-slate-800">
                                  Feedback para el Generador / Observaciones Técnicas:
                                </p>
                                <p className="mt-1 whitespace-pre-wrap text-slate-700 leading-relaxed">
                                  {ev.feedback_for_generator}
                                </p>
                              </div>
                            )}
                          </div>
                        )}
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
