import React from "react";

import {
  IncidentAnalysisResult,
  IncidentCategory,
  IncidentStatus,
} from "@/app/features/incidents/types/incidents";

type IncidentSummaryProps = {
  result: IncidentAnalysisResult;
};

const INVALID_RULE_LABELS: Record<string, string> = {
  invalid_tracking: "Tracking faltante o invalido",
  invalid_carrier: "Carrier invalido para el pais",
  invalid_category: "Categoria faltante o invalida",
  invalid_email: "Email faltante o invalido",
  closed_missing_score: "Cerrado sin puntuacion de satisfaccion",
  score_out_of_range: "Puntuacion de satisfaccion fuera de rango",
  invalid_country: "Country faltante o invalido",
  invalid_description: "Description vacia o muy corta",
};

const CATEGORY_LABELS: Record<IncidentCategory, string> = {
  LOST_PARCEL: "Paquete perdido",
  DELAYED_DELIVERY: "Retrasado",
  RETURN_REQUEST: "Devolucion",
  DAMAGE: "Daño",
  WRONG_ADDRESS: "Dirección incorrecta",
};

const STATUS_LABELS: Record<IncidentStatus, string> = {
  OPEN: "Abierta",
  CLOSED: "Cerrada",
  DISCARDED: "Descartada",
};

function toSentenceCaseLabel(value: string): string {
  return value
    .toLowerCase()
    .split("_")
    .map((word) => (word ? word[0].toUpperCase() + word.slice(1) : word))
    .join(" ");
}

function getDisplayLabel(key: string, labels?: Record<string, string>): string {
  return labels?.[key] ?? toSentenceCaseLabel(key);
}

function renderRows(
  counts: Record<string, number>,
  percentages?: Record<string, number>,
  labels?: Record<string, string>
): React.ReactNode {
  return Object.entries(counts).map(([key, value]) => (
    <li
      key={key}
      className="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-4 py-3 dark:border-slate-700/60 dark:bg-slate-800"
    >
      <span className="font-medium text-slate-700 dark:text-slate-200">{getDisplayLabel(key, labels)}</span>
      <span className="text-slate-700 dark:text-slate-300">
        {value}
        {percentages ? ` (${(percentages[key] ?? 0).toFixed(1)}%)` : ""}
      </span>
    </li>
  ));
}

export function IncidentSummary({ result }: IncidentSummaryProps) {
  return (
    <section className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-3">
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Total</p>
          <p className="mt-2 text-3xl font-semibold text-slate-950 dark:text-white">{result.total_records}</p>
        </article>
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Validos</p>
          <p className="mt-2 text-3xl font-semibold text-emerald-700 dark:text-emerald-400">{result.valid_records}</p>
        </article>
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Invalidos</p>
          <p className="mt-2 text-3xl font-semibold text-rose-700 dark:text-rose-400">{result.invalid_records}</p>
        </article>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <article className="rounded-2xl border border-slate-200 bg-slate-50 p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900/60">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Registros invalidos por tipo</h3>
          <ul className="mt-4 space-y-2">
            {Object.entries(result.invalid_breakdown).map(([rule, count]) => (
              <li
                key={rule}
                className="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-4 py-3 dark:border-slate-700/60 dark:bg-slate-800"
              >
                <span className="text-slate-700 dark:text-slate-300">{INVALID_RULE_LABELS[rule] ?? rule}</span>
                <span className="font-semibold text-slate-900 dark:text-white">{count}</span>
              </li>
            ))}
          </ul>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-slate-50 p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900/60">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Desglose por categoria</h3>
          <ul className="mt-4 space-y-2">
            {renderRows(result.by_category, result.category_percentages, CATEGORY_LABELS)}
          </ul>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-slate-50 p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900/60">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Desglose por estado</h3>
          <ul className="mt-4 space-y-2">
            {renderRows(result.by_status, result.status_percentages, STATUS_LABELS)}
          </ul>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-slate-50 p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900/60">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Indice de satisfaccion</h3>
          <p className="mt-3 text-sm text-slate-700 dark:text-slate-300">
            Incidencias puntuadas: {result.satisfaction.scored_incidents} de {result.satisfaction.closed_incidents}
          </p>
          <p className="text-sm text-slate-700 dark:text-slate-300">
            Promedio: {result.satisfaction.average.toFixed(2)} / 5.00
          </p>
          <ul className="mt-4 grid gap-2 sm:grid-cols-2">
            {Object.entries(result.satisfaction.counts).map(([score, count]) => (
              <li
                key={score}
                className="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-4 py-3 dark:border-slate-700/60 dark:bg-slate-800"
              >
                <span className="text-slate-700 dark:text-slate-300">Score {score}</span>
                <span className="font-semibold text-slate-900 dark:text-white">{count}</span>
              </li>
            ))}
          </ul>
        </article>
      </div>
    </section>
  );
}
