import React from "react";

import { IncidentAnalysisResult } from "@/app/features/incidents/types/incidents";

type IncidentSummaryProps = {
  result: IncidentAnalysisResult;
};

const INVALID_RULE_LABELS: Record<string, string> = {
  invalid_tracking: "Tracking faltante o invalido",
  invalid_carrier: "Carrier invalido para el pais",
  invalid_category: "Categoria faltante o invalida",
  invalid_email: "Email faltante o invalido",
  closed_missing_score: "CLOSED sin satisfaction_score",
  score_out_of_range: "satisfaction_score fuera de rango",
  invalid_country: "Country faltante o invalido",
  invalid_description: "Description vacia o muy corta",
};

function renderRows(
  counts: Record<string, number>,
  percentages?: Record<string, number>
): React.ReactNode {
  return Object.entries(counts).map(([key, value]) => (
    <li
      key={key}
      className="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-4 py-3"
    >
      <span className="font-medium text-slate-700">{key}</span>
      <span className="text-slate-700">
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
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Total</p>
          <p className="mt-2 text-3xl font-semibold text-slate-950">{result.total_records}</p>
        </article>
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Validos</p>
          <p className="mt-2 text-3xl font-semibold text-emerald-700">{result.valid_records}</p>
        </article>
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Invalidos</p>
          <p className="mt-2 text-3xl font-semibold text-rose-700">{result.invalid_records}</p>
        </article>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <article className="rounded-2xl border border-slate-200 bg-slate-50 p-5 shadow-sm">
          <h3 className="text-lg font-semibold text-slate-900">Registros invalidos por tipo</h3>
          <ul className="mt-4 space-y-2">
            {Object.entries(result.invalid_breakdown).map(([rule, count]) => (
              <li
                key={rule}
                className="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-4 py-3"
              >
                <span className="text-slate-700">{INVALID_RULE_LABELS[rule] ?? rule}</span>
                <span className="font-semibold text-slate-900">{count}</span>
              </li>
            ))}
          </ul>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-slate-50 p-5 shadow-sm">
          <h3 className="text-lg font-semibold text-slate-900">Desglose por categoria</h3>
          <ul className="mt-4 space-y-2">
            {renderRows(result.by_category, result.category_percentages)}
          </ul>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-slate-50 p-5 shadow-sm">
          <h3 className="text-lg font-semibold text-slate-900">Desglose por estado</h3>
          <ul className="mt-4 space-y-2">
            {renderRows(result.by_status, result.status_percentages)}
          </ul>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-slate-50 p-5 shadow-sm">
          <h3 className="text-lg font-semibold text-slate-900">Indice de satisfaccion</h3>
          <p className="mt-3 text-sm text-slate-700">
            Incidencias puntuadas: {result.satisfaction.scored_incidents} de {result.satisfaction.closed_incidents}
          </p>
          <p className="text-sm text-slate-700">
            Promedio: {result.satisfaction.average.toFixed(2)} / 5.00
          </p>
          <ul className="mt-4 grid gap-2 sm:grid-cols-2">
            {Object.entries(result.satisfaction.counts).map(([score, count]) => (
              <li
                key={score}
                className="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-4 py-3"
              >
                <span>Score {score}</span>
                <span className="font-semibold text-slate-900">{count}</span>
              </li>
            ))}
          </ul>
        </article>
      </div>
    </section>
  );
}
