"use client";

import React, { useCallback, useEffect, useState } from "react";

import { getIncidentSummary } from "@/app/features/incidents/services/incident-api";
import {
  BRANCH_LABELS,
  CATEGORY_LABELS,
  INCIDENT_BRANCHES,
  INCIDENT_CATEGORIES,
  INCIDENT_ORIGINS,
  INCIDENT_STATUSES,
  ORIGIN_LABELS,
  STATUS_LABELS,
} from "@/app/features/incidents/types/incident-domain";
import type { IncidentSummary } from "@/app/features/incidents/types/incident-domain";

export function IncidentSummaryPanel() {
  const [summary, setSummary] = useState<IncidentSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSummary = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getIncidentSummary();
      setSummary(data);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Error al cargar resumen";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchSummary();
  }, [fetchSummary]);

  if (isLoading) {
    return (
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold text-slate-950">
          Resumen de incidencias
        </h2>
        <div className="mt-6 flex items-center justify-center py-8">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-slate-200 border-t-slate-600" />
          <span className="ml-3 text-sm text-slate-500">
            Cargando resumen...
          </span>
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold text-slate-950">
          Resumen de incidencias
        </h2>
        <div className="mt-6 text-center py-8">
          <p className="text-sm text-rose-600">{error}</p>
          <button
            onClick={fetchSummary}
            className="mt-3 rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700"
          >
            Reintentar
          </button>
        </div>
      </section>
    );
  }

  if (!summary) {
    return null;
  }

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-xl font-semibold text-slate-950">
        Resumen de incidencias
      </h2>

      {/* Total card */}
      <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Total
          </p>
          <p className="mt-1 text-2xl font-semibold text-slate-950">
            {summary.total}
          </p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Abiertas
          </p>
          <p className="mt-1 text-2xl font-semibold text-blue-700">
            {summary.by_status.open ?? 0}
          </p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            En progreso
          </p>
          <p className="mt-1 text-2xl font-semibold text-amber-700">
            {summary.by_status.in_progress ?? 0}
          </p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Resueltas
          </p>
          <p className="mt-1 text-2xl font-semibold text-emerald-700">
            {summary.by_status.resolved ?? 0}
          </p>
        </div>
      </div>

      {/* Breakdown sections */}
      <div className="mt-6 grid gap-6 md:grid-cols-2">
        {/* By status */}
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <h3 className="text-sm font-semibold text-slate-900">Por estado</h3>
          <ul className="mt-3 space-y-1.5">
            {INCIDENT_STATUSES.map((status) => (
              <li
                key={status}
                className="flex items-center justify-between rounded-lg bg-white px-3 py-2 text-sm"
              >
                <span className="text-slate-700">
                  {STATUS_LABELS[status]}
                </span>
                <span className="font-semibold text-slate-900">
                  {summary.by_status[status] ?? 0}
                </span>
              </li>
            ))}
          </ul>
        </div>

        {/* By category */}
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <h3 className="text-sm font-semibold text-slate-900">
            Por categoría
          </h3>
          <ul className="mt-3 space-y-1.5">
            {INCIDENT_CATEGORIES.map((cat) => {
              const count = summary.by_category[cat] ?? 0;
              return (
                <li
                  key={cat}
                  className="flex items-center justify-between rounded-lg bg-white px-3 py-2 text-sm"
                >
                  <span className="text-slate-700">
                    {CATEGORY_LABELS[cat]}
                  </span>
                  <span className="font-semibold text-slate-900">
                    {count}
                  </span>
                </li>
              );
            })}
          </ul>
        </div>

        {/* By origin */}
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <h3 className="text-sm font-semibold text-slate-900">Por origen</h3>
          <ul className="mt-3 space-y-1.5">
            {INCIDENT_ORIGINS.map((origin) => (
              <li
                key={origin}
                className="flex items-center justify-between rounded-lg bg-white px-3 py-2 text-sm"
              >
                <span className="text-slate-700">
                  {ORIGIN_LABELS[origin]}
                </span>
                <span className="font-semibold text-slate-900">
                  {summary.by_origin[origin] ?? 0}
                </span>
              </li>
            ))}
          </ul>
        </div>

        {/* By branch */}
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <h3 className="text-sm font-semibold text-slate-900">Por sede</h3>
          <ul className="mt-3 space-y-1.5">
            {INCIDENT_BRANCHES.map((branch) => (
              <li
                key={branch}
                className="flex items-center justify-between rounded-lg bg-white px-3 py-2 text-sm"
              >
                <span className="text-slate-700">
                  {BRANCH_LABELS[branch]}
                </span>
                <span className="font-semibold text-slate-900">
                  {summary.by_branch[branch] ?? 0}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}