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

function renderMap(
  counts: Record<string, number>,
  percentages?: Record<string, number>
): React.ReactNode {
  return Object.entries(counts).map(([key, value]) => (
    <li
      key={key}
      className="flex items-center justify-between rounded-lg border border-zinc-200 bg-white px-3 py-2"
    >
      <span className="font-medium text-zinc-700">{key}</span>
      <span className="text-zinc-700">
        {value}
        {percentages && ` (${(percentages[key] ?? 0).toFixed(1)}%)`}
      </span>
    </li>
  ));
}

export function IncidentSummary({ result }: IncidentSummaryProps) {
  return (
    <section className="space-y-5 rounded-2xl border border-zinc-200 bg-zinc-50 p-5 shadow-sm">
      <header className="space-y-1">
        <h2 className="text-xl font-bold text-zinc-900">Resumen del analisis</h2>
        <p className="text-sm text-zinc-600">Archivo: {result.source_file}</p>
      </header>

      <div className="grid gap-3 sm:grid-cols-3">
        <article className="rounded-xl border border-zinc-200 bg-white p-4 text-center">
          <p className="text-xs uppercase tracking-wide text-zinc-500">Total</p>
          <p className="text-2xl font-bold text-zinc-900">{result.total_records}</p>
        </article>
        <article className="rounded-xl border border-zinc-200 bg-white p-4 text-center">
          <p className="text-xs uppercase tracking-wide text-zinc-500">Validos</p>
          <p className="text-2xl font-bold text-emerald-700">{result.valid_records}</p>
        </article>
        <article className="rounded-xl border border-zinc-200 bg-white p-4 text-center">
          <p className="text-xs uppercase tracking-wide text-zinc-500">Invalidos</p>
          <p className="text-2xl font-bold text-rose-700">{result.invalid_records}</p>
        </article>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <article className="space-y-2">
          <h3 className="text-lg font-semibold text-zinc-900">Invalidos por regla</h3>
          <ul className="space-y-2">
            {Object.entries(result.invalid_breakdown).map(([rule, count]) => (
              <li
                key={rule}
                className="flex items-center justify-between rounded-lg border border-zinc-200 bg-white px-3 py-2"
              >
                <span className="text-zinc-700">{INVALID_RULE_LABELS[rule] ?? rule}</span>
                <span className="font-semibold text-zinc-800">{count}</span>
              </li>
            ))}
          </ul>
        </article>

        <article className="space-y-2">
          <h3 className="text-lg font-semibold text-zinc-900">Categorias (validos)</h3>
          <ul className="space-y-2">
            {renderMap(result.by_category, result.category_percentages)}
          </ul>
        </article>

        <article className="space-y-2">
          <h3 className="text-lg font-semibold text-zinc-900">Estados (validos)</h3>
          <ul className="space-y-2">{renderMap(result.by_status, result.status_percentages)}</ul>
        </article>

        <article className="space-y-2">
          <h3 className="text-lg font-semibold text-zinc-900">Pais (validos)</h3>
          <ul className="space-y-2">{renderMap(result.by_country, result.country_percentages)}</ul>
        </article>
      </div>

      <article className="rounded-xl border border-zinc-200 bg-white p-4">
        <h3 className="mb-2 text-lg font-semibold text-zinc-900">Satisfaccion (CLOSED)</h3>
        <p className="text-sm text-zinc-700">
          Scored incidents: {result.satisfaction.scored_incidents} de {result.satisfaction.closed_incidents}
        </p>
        <p className="text-sm text-zinc-700">
          Average score: {result.satisfaction.average.toFixed(2)} / 5.00
        </p>
        <ul className="mt-3 grid gap-2 sm:grid-cols-2">
          {Object.entries(result.satisfaction.counts).map(([score, value]) => (
            <li
              key={score}
              className="flex items-center justify-between rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2"
            >
              <span>Score {score}</span>
              <span className="font-semibold">{value}</span>
            </li>
          ))}
        </ul>
      </article>
    </section>
  );
}
