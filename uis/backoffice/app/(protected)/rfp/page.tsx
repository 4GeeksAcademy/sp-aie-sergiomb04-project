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
  approval_status?: "pending" | "approved" | "rejected" | "changes_requested" | string | null;
  approver?: string | null;
  approved_at?: string | null;
  updated_at?: string | null;
};

type FinalDocumentData = {
  id: string;
  ticket_id: string;
  currency: string;
  generated_at?: string | null;
  sections?: {
    consolidated_markdown?: string;
    sections?: Record<string, unknown>;
    approvals?: Record<string, unknown>;
    arbitrations?: Array<{
      trigger_id: string;
      arbitrator: string;
      conflict_detected: string;
      applied_action: string;
    }>;
  };
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
    | "esperando_aprobación"
    | "terminado"
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

interface ArbitrationResolution {
  trigger_id: string;
  arbitrator: string;
  conflict_detected: string;
  applied_action: string;
}

interface ArbitrationResponse {
  ticket_id: string;
  conflict_count: number;
  resolutions?: ArbitrationResolution[];
  traces?: Array<{
    agent: string;
    input: unknown;
    output: unknown;
    timestamp: string;
  }>;
}

const STATUS_BADGE_STYLES: Record<string, { label: string; className: string }> = {
  analizando: {
    label: "Analizando (Pipeline en curso)",
    className: "bg-amber-100 text-amber-800 border-amber-300 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-900/50",
  },
  analisis_completo: {
    label: "Análisis Completo (Listo para Ventas)",
    className: "bg-emerald-100 text-emerald-800 border-emerald-300 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-900/50",
  },
  generando_borrador: {
    label: "Generando Borrador (Redacción en curso)",
    className: "bg-blue-100 text-blue-800 border-blue-300 dark:bg-blue-950/40 dark:text-blue-300 dark:border-blue-900/50",
  },
  en_evaluación: {
    label: "En Evaluación (Evaluadores paralelos)",
    className: "bg-purple-100 text-purple-800 border-purple-300 dark:bg-purple-950/40 dark:text-purple-300 dark:border-purple-900/50",
  },
  needs_human_review: {
    label: "Revisión Humana Requerida (Límite agotado)",
    className: "bg-amber-100 text-amber-900 border-amber-400 font-bold dark:bg-amber-950/50 dark:text-amber-200 dark:border-amber-700/60",
  },
  esperando_aprobación: {
    label: "Esperando Aprobación (HITL)",
    className: "bg-orange-100 text-orange-900 border-orange-300 font-semibold dark:bg-orange-950/50 dark:text-orange-200 dark:border-orange-700/60",
  },
  terminado: {
    label: "Terminado (Propuesta Completa)",
    className: "bg-emerald-100 text-emerald-900 border-emerald-400 font-bold dark:bg-emerald-950/50 dark:text-emerald-200 dark:border-emerald-700/60",
  },
  descartado: {
    label: "Descartado (No es RFP válida)",
    className: "bg-rose-100 text-rose-800 border-rose-300 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-900/50",
  },
};

export default function RFPIntakePage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);
  const [approvalError, setApprovalError] = useState<string | null>(null);
  const [activeTicketId, setActiveTicketId] = useState<string | null>(null);
  const [ticketDetail, setTicketDetail] = useState<RFPTicketBundle | null>(null);
  const [recentTickets, setRecentTickets] = useState<RFPTicketSummary[]>([]);
  const [finalDocument, setFinalDocument] = useState<FinalDocumentData | null>(null);
  const [arbitrationResult, setArbitrationResult] = useState<ArbitrationResponse | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
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

  const fetchFinalDoc = useCallback(async (ticketId: string) => {
    try {
      const res = await fetch(`/api/rfp/${encodeURIComponent(ticketId)}/final-document`, {
        cache: "no-store",
      });
      if (res.ok) {
        const doc = (await res.json()) as FinalDocumentData;
        setFinalDocument(doc);
      }
    } catch {
      // ignore
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

        if (data.status === "terminado") {
          void fetchFinalDoc(ticketId);
        }

        // Keep polling during active async steps
        const isStillRunning =
          data.status === "analizando" ||
          data.status === "generando_borrador";

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
    [fetchRecentTickets, fetchFinalDoc]
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
      setFinalDocument(null);
      setArbitrationResult(null);
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

  const handleInitiateApprovals = async () => {
    if (!ticketDetail) return;
    setActionLoading("initiate");
    setApprovalError(null);
    try {
      const res = await fetch(`/api/rfp/${encodeURIComponent(ticketDetail.ticket_id)}/approval/initiate`, {
        method: "POST",
      });
      if (res.ok) {
        void fetchTicketDetail(ticketDetail.ticket_id);
        void fetchRecentTickets();
      } else {
        const errData = await res.json().catch(() => null);
        setApprovalError(errData?.detail || `Error (${res.status}): no se pudo iniciar el ciclo de aprobaciones`);
      }
    } catch (err) {
      setApprovalError(err instanceof Error ? err.message : "Error de red al iniciar aprobaciones");
    } finally {
      setActionLoading(null);
    }
  };

  const handleDepartmentDecision = async (
    deptId: string,
    action: "approve" | "reject" | "request_changes",
    approver: string
  ) => {
    if (!ticketDetail) return;
    setActionLoading(`${deptId}-${action}`);
    setApprovalError(null);

    let notes: string | null = null;
    if (action === "request_changes") {
      notes = prompt("Indica las correcciones o ajustes necesarios para este departamento:") || "Ajustes requeridos.";
    }

    try {
      const res = await fetch(
        `/api/rfp/${encodeURIComponent(ticketDetail.ticket_id)}/approval/${encodeURIComponent(deptId)}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action, approver, notes }),
        }
      );

      if (res.ok) {
        setApprovalError(null);
        void fetchTicketDetail(ticketDetail.ticket_id);
        void fetchRecentTickets();
      } else {
        const errData = await res.json().catch(() => null);
        setApprovalError(
          errData?.detail || `Error (${res.status}): no se pudo registrar la decisión para ${deptId}`
        );
      }
    } catch (err) {
      setApprovalError(
        err instanceof Error ? err.message : "Error de conexión al registrar la decisión de aprobación"
      );
    } finally {
      setActionLoading(null);
    }
  };

  const handleRunArbitration = async () => {
    if (!ticketDetail) return;
    setActionLoading("arbitrate");
    try {
      const res = await fetch(`/api/rfp/${encodeURIComponent(ticketDetail.ticket_id)}/arbitrate`, {
        method: "POST",
      });
      if (res.ok) {
        const arb = await res.json();
        setArbitrationResult(arb);
      }
    } finally {
      setActionLoading(null);
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
        <span className="rounded bg-indigo-50 px-2.5 py-1 text-xs font-semibold uppercase tracking-wider text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
          TrackFlow Tech · Hito 9 (Partes 1, 2 y 3)
        </span>
        <h1 className="mt-2 text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl dark:text-white">
          Flujo Agéntico de RFPs: Aprobaciones Humanas (HITL), Arbitraje y Cierre
        </h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Recepción automatizada, triage con clasificador, generación por departamentos,
          evaluación en paralelo, aprobación humana aislada (interrupt/resume) y síntesis del documento final (§7).
        </p>
      </div>

      {/* Main Grid: Upload + Recent Tickets */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Upload Form Card */}
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center gap-2 border-b border-slate-100 pb-3 dark:border-slate-800">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-600 text-xs font-bold text-white">
              1
            </span>
            <h2 className="text-base font-bold text-slate-900 dark:text-white">
              Subida de RFP en PDF (Modo Ticket)
            </h2>
          </div>
          <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
            Sube la solicitud recibida. Se guardará en <code>data/raw/</code> y creará un ticket en PostgreSQL.
          </p>

          <form onSubmit={handleUploadSubmit} className="mt-4 flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <label
                htmlFor="rfp-file-input"
                className="text-xs font-medium text-slate-700 dark:text-slate-300"
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
                className="block w-full cursor-pointer rounded-xl border border-slate-300 bg-slate-50/50 px-3 py-2 text-xs text-slate-800 file:mr-3 file:rounded-lg file:border-0 file:bg-indigo-50 file:px-3 file:py-1.5 file:text-xs file:font-semibold file:text-indigo-700 hover:file:bg-indigo-100 dark:border-slate-700 dark:bg-slate-800/60 dark:text-slate-200 dark:file:bg-indigo-950 dark:file:text-indigo-300 dark:hover:file:bg-indigo-900"
              />
            </div>

            {selectedFile && (
              <div className="rounded-lg bg-slate-50 p-2.5 text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                <span className="font-semibold text-slate-800 dark:text-white">Seleccionado:</span>{" "}
                {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
              </div>
            )}

            {uploadError && (
              <div
                id="rfp-upload-error"
                className="rounded-lg border border-rose-200 bg-rose-50 p-2.5 text-xs text-rose-700 dark:border-rose-900/50 dark:bg-rose-950/40 dark:text-rose-300"
              >
                {uploadError}
              </div>
            )}

            <button
              id="rfp-upload-submit-btn"
              type="submit"
              disabled={!selectedFile || uploading}
              className="flex items-center justify-center rounded-xl bg-indigo-600 px-4 py-2.5 text-xs font-semibold text-white shadow-sm transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-slate-300 dark:disabled:bg-slate-800 dark:disabled:text-slate-600"
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
        <section className="col-span-1 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900 lg:col-span-2">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
            <h2 className="text-base font-bold text-slate-900 dark:text-white">
              Historial de Tickets RFP en PostgreSQL
            </h2>
            <button
              onClick={() => void fetchRecentTickets()}
              className="rounded-lg px-2.5 py-1 text-xs font-medium text-indigo-600 hover:bg-indigo-50 dark:text-indigo-400 dark:hover:bg-indigo-950/40"
            >
              Refrescar lista
            </button>
          </div>

          <div className="mt-3 max-h-64 overflow-y-auto">
            {recentTickets.length === 0 ? (
              <p className="py-6 text-center text-xs text-slate-400 dark:text-slate-500">
                No hay tickets registrados aún. Sube un PDF para comenzar.
              </p>
            ) : (
              <div className="divide-y divide-slate-100 dark:divide-slate-800">
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
                      className={`flex cursor-pointer items-center justify-between p-3 text-xs transition hover:bg-slate-50 dark:hover:bg-slate-800/60 ${
                        isSelected ? "bg-indigo-50/60 font-semibold dark:bg-indigo-950/60" : ""
                      }`}
                    >
                      <div className="flex flex-col gap-0.5">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-bold text-indigo-900 dark:text-indigo-300">
                            {t.rfp_id}
                          </span>
                          <span className="text-slate-700 dark:text-slate-300">
                            {t.client_name || t.original_filename || "Sin nombre"}
                          </span>
                          {t.client_country && (
                            <span className="text-slate-400 dark:text-slate-500">
                              ({t.client_country})
                            </span>
                          )}
                        </div>
                        <span className="text-[11px] text-slate-400 dark:text-slate-500">
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
          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm font-bold text-indigo-700 dark:text-indigo-300">
                    {ticketDetail.rfp_id}
                  </span>
                  <span className="text-xs text-slate-400">
                    ID: {ticketDetail.ticket_id}
                  </span>
                </div>
                <h2 className="mt-1 text-lg font-bold text-slate-900 dark:text-white">
                  {ticketDetail.metadata?.client_name ||
                    ticketDetail.original_filename ||
                    "Documento RFP"}
                </h2>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Archivo guardado en: <code>{ticketDetail.pdf_path}</code>
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                {polling && (
                  <div className="flex items-center gap-1.5 text-xs text-indigo-600">
                    <span className="h-2.5 w-2.5 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent" />
                    <span>Actualizando...</span>
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

                {/* Part 2: Generation Trigger Button */}
                {(ticketDetail.status === "analisis_completo" ||
                  ticketDetail.status === "en_evaluación" ||
                  ticketDetail.status === "needs_human_review") && (
                  <button
                    id="trigger-generate-btn"
                    onClick={() => void handleTriggerGeneration()}
                    disabled={generating || polling}
                    className="flex items-center gap-1.5 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-bold text-white shadow hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-slate-300"
                  >
                    {generating ? (
                      <>
                        <span className="h-3 w-3 animate-spin rounded-full border-2 border-white border-t-transparent" />
                        Generando...
                      </>
                    ) : (
                      <>⚡ Generar Propuesta Económica</>
                    )}
                  </button>
                )}

                {/* Part 3: Initiate Approval Cycle Button */}
                {(ticketDetail.status === "en_evaluación" ||
                  ticketDetail.status === "needs_human_review") && (
                  <button
                    id="trigger-init-approval-btn"
                    onClick={() => void handleInitiateApprovals()}
                    disabled={actionLoading === "initiate"}
                    className="flex items-center gap-1.5 rounded-xl bg-orange-600 px-4 py-2 text-xs font-bold text-white shadow hover:bg-orange-500 disabled:cursor-not-allowed disabled:bg-slate-300"
                  >
                    {actionLoading === "initiate" ? "Iniciando..." : "🚀 Iniciar Aprobaciones (HITL)"}
                  </button>
                )}

                {/* Arbitration Button */}
                <button
                  id="trigger-arbitrate-btn"
                  onClick={() => void handleRunArbitration()}
                  disabled={actionLoading === "arbitrate"}
                  className="flex items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-sm hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                >
                  {actionLoading === "arbitrate" ? "Verificando..." : "⚖️ Arbitraje (§7)"}
                </button>
              </div>
            </div>

            {generateError && (
              <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800">
                {generateError}
              </div>
            )}

            {/* Arbitration Result Panel */}
            {arbitrationResult && (
              <div className="mt-4 rounded-xl border border-indigo-200 bg-indigo-50/70 p-4 text-xs dark:border-indigo-900/50 dark:bg-indigo-950/40">
                <div className="flex items-center justify-between border-b border-indigo-200 pb-2 dark:border-indigo-900/50">
                  <span className="font-bold text-indigo-950 dark:text-indigo-200">
                    Resultado de Arbitraje Fijo (§7 BRIEFING): {arbitrationResult.conflict_count} conflictos detectados
                  </span>
                  <button
                    onClick={() => setArbitrationResult(null)}
                    className="text-slate-400 hover:text-slate-600"
                  >
                    Cerrar
                  </button>
                </div>
                {arbitrationResult.conflict_count === 0 ? (
                  <p className="mt-2 text-indigo-900 dark:text-indigo-200">
                    No se detectaron contradicciones estructurales entre departamentos ni de moneda.
                  </p>
                ) : (
                  <div className="mt-2 space-y-2">
                    {arbitrationResult.resolutions?.map((r: ArbitrationResolution, idx: number) => (
                      <div key={idx} className="rounded-lg bg-white p-3 shadow-xs dark:bg-slate-800 dark:border dark:border-slate-700">
                        <div className="flex items-center justify-between">
                          <span className="font-mono font-bold text-indigo-800 dark:text-indigo-300">
                            Trigger: {r.trigger_id}
                          </span>
                          <span className="font-semibold text-slate-700 dark:text-slate-300">
                            Árbitro Fijo: {r.arbitrator}
                          </span>
                        </div>
                        <p className="mt-1 text-slate-600 dark:text-slate-400">{r.conflict_detected}</p>
                        <p className="mt-1 font-medium text-emerald-800 dark:text-emerald-400">
                          Acción de Resolución: {r.applied_action}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Needs Human Review Warning Banner */}
            {ticketDetail.status === "needs_human_review" && (
              <div
                id="rfp-needs-human-review-banner"
                className="mt-4 rounded-xl border-2 border-amber-300 bg-amber-50 p-4 text-xs text-amber-900 shadow-sm dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200"
              >
                <div className="flex items-center gap-2">
                  <span className="rounded bg-amber-200 px-2 py-0.5 font-bold text-amber-900 dark:bg-amber-900 dark:text-amber-200">
                    ⚠️ ACCIÓN REQUERIDA
                  </span>
                  <p className="font-bold text-amber-950 dark:text-amber-100">
                    Revisión Humana Requerida — Límite de Iteraciones Agotado
                  </p>
                </div>
                <p className="mt-1.5 leading-relaxed text-amber-900 dark:text-amber-300">
                  Una o más secciones generadas han agotado el límite de reintentos del ciclo generador-evaluador sin superar la totalidad de los criterios automatizados.
                  El último borrador generado se ha conservado como <strong>provisional</strong>. El ticket <strong>no ha sido descartado</strong>.
                </p>
              </div>
            )}

            {/* Finished State Banner */}
            {ticketDetail.status === "terminado" && (
              <div
                id="rfp-terminado-banner"
                className="mt-4 rounded-xl border-2 border-emerald-400 bg-emerald-50 p-4 text-xs text-emerald-950 shadow-sm dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200"
              >
                <div className="flex items-center gap-2">
                  <span className="rounded bg-emerald-200 px-2 py-0.5 font-bold text-emerald-900 dark:bg-emerald-900 dark:text-emerald-200">
                    🎉 PROPUESTA COMPLETADA
                  </span>
                  <p className="font-bold text-emerald-950 dark:text-emerald-100">
                    Todos los Departamentos Han Aprobado Formalmente la Propuesta
                  </p>
                </div>
                <p className="mt-1.5 leading-relaxed text-emerald-900 dark:text-emerald-300">
                  El documento final consolidado ha sido sintetizado automáticamente y guardado en PostgreSQL (<code>RFPFinalDocument</code>). Listo para entrega formal al cliente.
                </p>
              </div>
            )}
          </section>

          {/* Final Document View (when status is terminado) */}
          {finalDocument && ticketDetail.status === "terminado" && (
            <section
              id="rfp-final-document-section"
              className="rounded-2xl border-2 border-emerald-300 bg-white p-6 shadow-md dark:border-emerald-800 dark:bg-slate-900"
            >
              <div className="flex items-center justify-between border-b border-slate-100 pb-4 dark:border-slate-800">
                <div>
                  <span className="rounded bg-emerald-100 px-2.5 py-1 text-xs font-bold text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300">
                    RFP Final Document (Consolidado Oficial)
                  </span>
                  <h3 className="mt-1 text-lg font-bold text-slate-900 dark:text-white">
                    Propuesta Económica Lista para Envío Comercial
                  </h3>
                </div>
                <div className="text-right text-xs text-slate-500 dark:text-slate-400">
                  <p>Moneda: <strong>{finalDocument.currency}</strong></p>
                  <p>Generado: {finalDocument.generated_at ? new Date(finalDocument.generated_at).toLocaleString() : ""}</p>
                </div>
              </div>

              <div className="mt-4 rounded-xl bg-slate-50 p-5 font-mono text-xs leading-relaxed text-slate-800 whitespace-pre-wrap max-h-[500px] overflow-y-auto dark:border dark:border-slate-800 dark:bg-slate-950 dark:text-slate-200">
                {finalDocument.sections?.consolidated_markdown || JSON.stringify(finalDocument.sections, null, 2)}
              </div>
            </section>
          )}

          {/* Department Breakdown & HITL Approval Gates (Milestone 9 - Part 3) */}
          {ticketDetail.department_sections &&
            ticketDetail.department_sections.length > 0 && (
              <section className="flex flex-col gap-6">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                    Departamentos y Aprobaciones Humanas (HITL Gates)
                  </h3>
                  <span className="text-xs text-slate-500 dark:text-slate-400">
                    Ana Whitfield · Carlos Vega · Sofía Ramos · Miguel Torres (Arbitraje)
                  </span>
                </div>

                {approvalError && (
                  <div className="flex items-center justify-between rounded-xl border border-rose-300 bg-rose-50 p-4 text-xs font-semibold text-rose-800 dark:border-rose-800/60 dark:bg-rose-950/40 dark:text-rose-300">
                    <span>❌ {approvalError}</span>
                    <button
                      onClick={() => setApprovalError(null)}
                      className="ml-4 font-bold underline hover:text-rose-900 dark:hover:text-rose-100"
                    >
                      Cerrar
                    </button>
                  </div>
                )}

                <div className="grid grid-cols-1 gap-6">
                  {ticketDetail.department_sections.map((sec) => {
                    const isDraftReady = Boolean(sec.draft_content);
                    const isApproved = sec.approval_status === "approved";
                    const isRejected = sec.approval_status === "rejected";
                    const isChanges = sec.approval_status === "changes_requested";

                    return (
                      <div
                        key={sec.id}
                        className={`flex flex-col rounded-2xl border p-6 shadow-sm dark:bg-slate-900 ${
                          isApproved
                            ? "border-emerald-300 ring-2 ring-emerald-100 bg-white dark:border-emerald-800 dark:ring-emerald-950"
                            : isRejected
                            ? "border-rose-300 ring-2 ring-rose-100 bg-white dark:border-rose-800 dark:ring-rose-950"
                            : "border-slate-200 bg-white dark:border-slate-800"
                        }`}
                      >
                        {/* Section Header */}
                        <div className="flex flex-col justify-between gap-2 border-b border-slate-100 pb-4 dark:border-slate-800 sm:flex-row sm:items-center">
                          <div className="flex items-center gap-3">
                            <span className="rounded-lg bg-indigo-100 px-2.5 py-1 font-mono text-xs font-bold text-indigo-800 dark:bg-indigo-950 dark:text-indigo-300">
                              {sec.department_id}
                            </span>
                            <div>
                              <h4 className="text-base font-bold text-slate-900 dark:text-white">
                                {sec.department}
                              </h4>
                              <p className="text-xs text-slate-500 dark:text-slate-400">
                                Responsable Designado: <strong>{sec.contact_person}</strong>
                              </p>
                            </div>
                          </div>

                          {/* Approval Status Badges */}
                          <div className="flex items-center gap-2">
                            {isApproved && (
                              <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-800 border border-emerald-300">
                                ✅ Aprobado formalmente
                              </span>
                            )}
                            {isRejected && (
                              <span className="rounded-full bg-rose-100 px-3 py-1 text-xs font-bold text-rose-800 border border-rose-300">
                                ❌ Rechazado
                              </span>
                            )}
                            {isChanges && (
                              <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-bold text-amber-800 border border-amber-300">
                                ⚠️ Cambios Solicitados
                              </span>
                            )}
                            {!isApproved && !isRejected && !isChanges && (
                              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                                Pendiente de Aprobación
                              </span>
                            )}
                          </div>
                        </div>

                        {/* HITL Approval Decision Action Controls */}
                        {isDraftReady && (
                          <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl bg-slate-50 p-3.5 border border-slate-200 dark:bg-slate-800/80 dark:border-slate-700">
                            <div>
                              <span className="text-xs font-bold text-slate-900 dark:text-white">
                                Sign-off de {sec.contact_person}:
                              </span>
                              <p className="text-[11px] text-slate-500 dark:text-slate-400">
                                Interrupción LangGraph (interrupt/resume). Revisión independiente por departamento.
                              </p>
                            </div>

                            <div className="flex flex-wrap items-center gap-2">
                              <button
                                onClick={() =>
                                  void handleDepartmentDecision(
                                    sec.department_id,
                                    "approve",
                                    sec.contact_person
                                  )
                                }
                                disabled={actionLoading != null}
                                className="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-bold text-white shadow-xs hover:bg-emerald-500 disabled:bg-slate-300"
                              >
                                {actionLoading === `${sec.department_id}-approve`
                                  ? "Aprobando..."
                                  : "✅ Aprobar"}
                              </button>
                              <button
                                onClick={() =>
                                  void handleDepartmentDecision(
                                    sec.department_id,
                                    "request_changes",
                                    sec.contact_person
                                  )
                                }
                                disabled={actionLoading != null}
                                className="rounded-lg border border-amber-400 bg-amber-50 px-3 py-1.5 text-xs font-bold text-amber-900 hover:bg-amber-100 disabled:bg-slate-300 dark:border-amber-700 dark:bg-amber-950/40 dark:text-amber-300 dark:hover:bg-amber-950/60 dark:disabled:bg-slate-800"
                              >
                                {actionLoading === `${sec.department_id}-request_changes`
                                  ? "Enviando..."
                                  : "⚠️ Solicitar Cambios"}
                              </button>
                              <button
                                onClick={() =>
                                  void handleDepartmentDecision(
                                    sec.department_id,
                                    "reject",
                                    sec.contact_person
                                  )
                                }
                                disabled={actionLoading != null}
                                className="rounded-lg border border-rose-300 bg-white px-3 py-1.5 text-xs font-bold text-rose-700 hover:bg-rose-50 disabled:bg-slate-300 dark:border-rose-800 dark:bg-slate-800 dark:text-rose-400 dark:hover:bg-rose-950/40 dark:disabled:bg-slate-800"
                              >
                                {actionLoading === `${sec.department_id}-reject`
                                  ? "Rechazando..."
                                  : "❌ Rechazar"}
                              </button>
                            </div>
                          </div>
                        )}

                        {/* Generated Draft Section */}
                        {isDraftReady && (
                          <div className="mt-4 flex flex-col gap-2">
                            <h5 className="text-xs font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400">
                              Borrador Económico Propuesto
                            </h5>
                            <div className="rounded-xl border border-slate-200 bg-slate-900/5 p-4 font-mono text-xs text-slate-800 whitespace-pre-wrap leading-relaxed max-h-60 overflow-y-auto dark:border-slate-800 dark:bg-slate-950 dark:text-slate-200">
                              {sec.draft_content}
                            </div>
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
