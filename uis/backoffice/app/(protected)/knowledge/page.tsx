"use client";

import { useState } from "react";

const SUGGESTED_QUERIES = [
  {
    category: "SLA y Envíos",
    question: "¿Cuáles son los tiempos de entrega estándar y express en España y Estados Unidos?",
  },
  {
    category: "Picos de Demanda",
    question: "¿Cómo se gestiona el SLA de entrega durante Black Friday y rebajas?",
  },
  {
    category: "Devoluciones",
    question: "¿Cuál es la ventana de devolución estándar y cómo se tratan las devoluciones internacionales?",
  },
  {
    category: "Transportistas",
    question: "¿Qué transportista tiene mejor cobertura en zonas rurales de Aragón?",
  },
  {
    category: "Tarifas",
    question: "¿Cuáles son las tarifas de almacenamiento y qué condiciones aplican para inventario de larga duración?",
  },
  {
    category: "Negociación",
    question: "¿Puede un account manager autorizar un descuento de almacenamiento directamente?",
  },
];

export default function KnowledgeQueryPage() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastAskedQuestion, setLastAskedQuestion] = useState<string | null>(null);

  const handleSubmit = async (qToAsk?: string) => {
    const q = (qToAsk ?? question).trim();
    if (!q) return;

    setLoading(true);
    setError(null);
    setAnswer(null);
    setLastAskedQuestion(q);

    try {
      const res = await fetch("/api/knowledge/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q }),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(
          errJson.detail || `Error en la solicitud (Código ${res.status})`
        );
      }

      const data = await res.json();
      setAnswer(data.answer);
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Error al consultar la base de conocimiento."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-1 flex-col gap-8 p-6 lg:p-10">
      {/* Header */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-3">
          <span className="rounded-md bg-indigo-50 px-2.5 py-1 text-xs font-semibold uppercase tracking-wider text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
            Base de Conocimiento RAG
          </span>
          <span className="text-xs text-slate-500">Colección: trackflow_knowledge</span>
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white lg:text-3xl">
          Asistente Comercial y Operativo
        </h1>
        <p className="max-w-3xl text-sm text-slate-600 dark:text-slate-400">
          Consulta en lenguaje natural sobre políticas internas, acuerdos de nivel de servicio (SLA),
          cobertura de transportistas y tarifas de almacenamiento de TrackFlow. Las respuestas son
          generadas estrictamente a partir de los documentos oficiales indexados.
        </p>
      </div>

      {/* Query input card */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSubmit();
          }}
          className="flex flex-col gap-4"
        >
          <label
            htmlFor="rag-question-input"
            className="text-sm font-medium text-slate-700 dark:text-slate-300"
          >
            Escribe tu consulta:
          </label>
          <div className="flex flex-col gap-3 sm:flex-row">
            <textarea
              id="rag-question-input"
              rows={3}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ej: ¿Cuál es el SLA comprometido mensualmente y qué compensación aplica si se incumple?"
              className="flex-1 rounded-xl border border-slate-300 bg-slate-50/50 p-3.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-indigo-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 dark:border-slate-700 dark:bg-slate-800/60 dark:text-white dark:focus:bg-slate-800"
              disabled={loading}
            />
            <button
              id="rag-submit-btn"
              type="submit"
              disabled={loading || !question.trim()}
              className="inline-flex items-center justify-center rounded-xl bg-indigo-600 px-6 py-3 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-indigo-500 dark:hover:bg-indigo-600 sm:self-end"
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <svg
                    className="h-4 w-4 animate-spin text-white"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                  Consultando...
                </span>
              ) : (
                "Consultar"
              )}
            </button>
          </div>
        </form>

        {/* Suggested queries */}
        <div className="mt-6 border-t border-slate-100 pt-4 dark:border-slate-800">
          <p className="mb-2.5 text-xs font-semibold uppercase tracking-wider text-slate-500">
            Consultas frecuentes recomendadas:
          </p>
          <div className="flex flex-wrap gap-2">
            {SUGGESTED_QUERIES.map((sq) => (
              <button
                key={sq.question}
                type="button"
                onClick={() => {
                  setQuestion(sq.question);
                  handleSubmit(sq.question);
                }}
                disabled={loading}
                className="group inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:border-indigo-300 hover:bg-indigo-50/50 hover:text-indigo-700 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800/80 dark:text-slate-300 dark:hover:bg-indigo-950/40 dark:hover:text-indigo-300"
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
              <p className="font-semibold">Ocurrió un error al procesar la consulta</p>
              <p className="mt-1 text-xs opacity-90">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Answer display */}
      {answer && (
        <div
          id="rag-answer-box"
          className="rounded-2xl border border-indigo-100 bg-gradient-to-b from-white to-slate-50 p-6 shadow-sm dark:border-indigo-950 dark:from-slate-900 dark:to-slate-900/80"
        >
          <div className="flex items-center justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
            <div className="flex items-center gap-2">
              <span className="flex h-2.5 w-2.5 rounded-full bg-emerald-500" />
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400">
                Respuesta generada por el Asistente
              </span>
            </div>
            {lastAskedQuestion && (
              <span className="max-w-md truncate text-xs text-slate-400">
                Q: &ldquo;{lastAskedQuestion}&rdquo;
              </span>
            )}
          </div>
          <div className="mt-4 text-sm leading-relaxed text-slate-800 dark:text-slate-200">
            {answer.split("\n").map((paragraph, idx) => (
              <p key={idx} className={idx > 0 ? "mt-3" : ""}>
                {paragraph}
              </p>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
