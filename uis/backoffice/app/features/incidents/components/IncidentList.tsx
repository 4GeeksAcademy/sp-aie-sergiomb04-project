"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";

import {
  listIncidents,
  updateIncidentStatus,
} from "@/app/features/incidents/services/incident-api";
import {
  BRANCH_LABELS,
  CATEGORY_LABELS,
  INCIDENT_BRANCHES,
  INCIDENT_ORIGINS,
  INCIDENT_STATUSES,
  ORIGIN_LABELS,
  STATUS_LABELS,
  getNextStatuses,
} from "@/app/features/incidents/types/incident-domain";
import type {
  Incident,
  IncidentStatus,
} from "@/app/features/incidents/types/incident-domain";

export function IncidentList() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [filterStatus, setFilterStatus] = useState("");
  const [filterOrigin, setFilterOrigin] = useState("");
  const [filterBranch, setFilterBranch] = useState("");

  // Status update tracking
  const [updatingId, setUpdatingId] = useState<string | null>(null);
  const [updateError, setUpdateError] = useState<string | null>(null);

  const fetchIncidents = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const filters: Record<string, string> = {};
      if (filterStatus) filters.status = filterStatus;
      if (filterOrigin) filters.origin = filterOrigin;
      if (filterBranch) filters.branch = filterBranch;
      const data = await listIncidents(filters);
      setIncidents(data);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Error al cargar incidencias";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [filterStatus, filterOrigin, filterBranch]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchIncidents();
  }, [fetchIncidents]);

  useEffect(() => {
    const handleIncidentsUpdated = () => {
      void fetchIncidents();
    };
    window.addEventListener("trackflow:incidents-updated", handleIncidentsUpdated);
    return () => {
      window.removeEventListener("trackflow:incidents-updated", handleIncidentsUpdated);
    };
  }, [fetchIncidents]);

  const handleStatusChange = useCallback(
    async (incidentId: string, newStatus: IncidentStatus) => {
      // Optimistic update
      const previousIncidents = [...incidents];
      setIncidents((prev) =>
        prev.map((inc) =>
          inc.id === incidentId ? { ...inc, status: newStatus } : inc,
        ),
      );
      setUpdatingId(incidentId);
      setUpdateError(null);

      try {
        await updateIncidentStatus(incidentId, { status: newStatus });
        if (typeof window !== "undefined") {
          window.dispatchEvent(new CustomEvent("trackflow:incidents-updated"));
        }
      } catch (err: unknown) {
        // Rollback on failure
        setIncidents(previousIncidents);
        const message =
          err instanceof Error
            ? err.message
            : "Error al actualizar el estado";
        setUpdateError(message);
      } finally {
        setUpdatingId(null);
      }
    },
    [incidents],
  );

  const isEmpty = !isLoading && !error && incidents.length === 0;

  const activeFiltersCount = useMemo(
    () => [filterStatus, filterOrigin, filterBranch].filter(Boolean).length,
    [filterStatus, filterOrigin, filterBranch],
  );

  return (
    <section className="space-y-6">
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <h2 className="text-xl font-semibold text-slate-950 dark:text-white">
          Listado de incidencias
        </h2>

        {/* Filters */}
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <div>
            <label
              htmlFor="filter-status"
              className="block text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400"
            >
              Estado
            </label>
            <select
              id="filter-status"
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="mt-1 block w-full rounded-xl border border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-900 focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100 dark:focus:border-slate-400 dark:focus:ring-slate-400"
            >
              <option value="">Todos</option>
              {INCIDENT_STATUSES.map((s) => (
                <option key={s} value={s}>
                  {STATUS_LABELS[s]}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label
              htmlFor="filter-origin"
              className="block text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400"
            >
              Origen
            </label>
            <select
              id="filter-origin"
              value={filterOrigin}
              onChange={(e) => setFilterOrigin(e.target.value)}
              className="mt-1 block w-full rounded-xl border border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-900 focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100 dark:focus:border-slate-400 dark:focus:ring-slate-400"
            >
              <option value="">Todos</option>
              {INCIDENT_ORIGINS.map((o) => (
                <option key={o} value={o}>
                  {ORIGIN_LABELS[o]}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label
              htmlFor="filter-branch"
              className="block text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400"
            >
              Sede
            </label>
            <select
              id="filter-branch"
              value={filterBranch}
              onChange={(e) => setFilterBranch(e.target.value)}
              className="mt-1 block w-full rounded-xl border border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-900 focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100 dark:focus:border-slate-400 dark:focus:ring-slate-400"
            >
              <option value="">Todas</option>
              {INCIDENT_BRANCHES.map((b) => (
                <option key={b} value={b}>
                  {BRANCH_LABELS[b]}
                </option>
              ))}
            </select>
          </div>
        </div>

        {activeFiltersCount > 0 && (
          <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
            Filtros activos: {activeFiltersCount}
          </p>
        )}

        {updateError && (
          <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-900/50 dark:bg-rose-950/40 dark:text-rose-400">
            {updateError}
          </div>
        )}

        {/* Loading state */}
        {isLoading && (
          <div className="mt-6 flex items-center justify-center py-12">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-slate-200 border-t-slate-600 dark:border-slate-700 dark:border-t-slate-400" />
            <span className="ml-3 text-sm text-slate-500 dark:text-slate-400">
              Cargando incidencias...
            </span>
          </div>
        )}

        {/* Error state */}
        {!isLoading && error && (
          <div className="mt-6 text-center py-12">
            <p className="text-sm text-rose-600">{error}</p>
            <button
              onClick={fetchIncidents}
              className="mt-3 rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700 dark:bg-white dark:text-slate-950 dark:hover:bg-slate-200"
            >
              Reintentar
            </button>
          </div>
        )}

        {/* Empty state */}
        {isEmpty && (
          <div className="mt-6 rounded-xl border border-dashed border-slate-300 bg-slate-50 py-12 text-center dark:border-slate-800 dark:bg-slate-900/40">
            <p className="text-sm text-slate-500 dark:text-slate-400">
              No hay incidencias que coincidan con los filtros.
            </p>
          </div>
        )}

        {/* Incident list */}
        {!isLoading && !error && incidents.length > 0 && (
          <div className="mt-6 space-y-3">
            {incidents.map((incident) => {
              const nextStatuses = getNextStatuses(incident.status);
              return (
                <div
                  key={incident.id}
                  className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-800/60"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <h3 className="font-semibold text-slate-900 dark:text-white">
                        {incident.title}
                      </h3>
                      <p className="mt-1 text-sm text-slate-600 line-clamp-2 dark:text-slate-300">
                        {incident.description}
                      </p>
                      <div className="mt-2 flex flex-wrap gap-2 text-xs">
                        <span className="rounded-lg bg-slate-200 px-2 py-1 text-slate-700 dark:bg-slate-700 dark:text-slate-200">
                          {CATEGORY_LABELS[incident.category] ??
                            incident.category}
                        </span>
                        <span
                          className={`rounded-lg px-2 py-1 font-medium ${
                            incident.status === "open"
                              ? "bg-blue-100 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300"
                              : incident.status === "in_progress"
                                ? "bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300"
                                : incident.status === "resolved"
                                  ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300"
                                  : "bg-slate-200 text-slate-500 dark:bg-slate-800 dark:text-slate-400"
                          }`}
                        >
                          {STATUS_LABELS[incident.status]}
                        </span>
                        <span className="rounded-lg bg-slate-200 px-2 py-1 text-slate-700 dark:bg-slate-700 dark:text-slate-200">
                          {ORIGIN_LABELS[incident.origin]}
                        </span>
                        <span className="rounded-lg bg-slate-200 px-2 py-1 text-slate-700 dark:bg-slate-700 dark:text-slate-200">
                          {BRANCH_LABELS[incident.branch]}
                        </span>
                      </div>
                    </div>

                    {/* Status update buttons */}
                    {nextStatuses.length > 0 && (
                      <div className="flex shrink-0 flex-col gap-1.5">
                        {nextStatuses.map((nextStatus) => (
                          <button
                            key={nextStatus}
                            onClick={() =>
                              handleStatusChange(incident.id, nextStatus)
                            }
                            disabled={updatingId === incident.id}
                            className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                          >
                            {updatingId === incident.id
                              ? "Actualizando..."
                              : `→ ${STATUS_LABELS[nextStatus]}`}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}
