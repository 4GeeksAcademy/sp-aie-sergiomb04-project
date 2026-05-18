"use client";

import React, { useCallback, useState } from "react";
import { createCandidate, fetchCandidates } from "../../../services/api";
import { CandidateFilters } from "./CandidateFilters";
import { CandidatesTable } from "@/app/components/candidates/CandidatesTable";
import { Candidate, CandidateFilters as CandidateFiltersType, CandidateListResponse, CandidatePayload } from "./types";
import { DEFAULT_FILTERS, FiltersState } from "./utils";
import { CandidateForm } from "./CandidateForm";

function toApiFilters(filters: FiltersState) {
  return {
    status: filters.status || undefined,
    stage: filters.stage || undefined,
    search: filters.search.trim() || undefined,
    page: filters.page,
    limit: filters.limit,
  };
}

function toSearchParams(filters: FiltersState): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.stage) params.set("stage", filters.stage);
  if (filters.search) params.set("search", filters.search);
  params.set("page", String(filters.page));
  params.set("limit", String(filters.limit));
  return params;
}

type CandidatesDashboardProps = {
  initialCandidates: Candidate[];
  initialError: string | null;
  initialFilters: CandidateFiltersType;
};

function normalizeFilters(filters: CandidateFiltersType): FiltersState {
  return {
    status: filters.status || "",
    stage: filters.stage || "",
    search: filters.search || "",
    page: filters.page || 1,
    limit: filters.limit || 20,
  };
}

export function CandidatesDashboard({
  initialCandidates,
  initialError,
  initialFilters,
}: CandidatesDashboardProps) {
  const [filters, setFilters] = useState<FiltersState>(() => normalizeFilters(initialFilters));
  const [candidates, setCandidates] = useState<Candidate[]>(initialCandidates);
  const [error, setError] = useState<string | null>(initialError);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(
    initialError ? null : "Datos cargados correctamente"
  );
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [createSuccess, setCreateSuccess] = useState<string | null>(null);

  const loadCandidates = useCallback(async (activeFilters: FiltersState) => {
    setIsLoading(true);
    setSuccessMessage(null);
    try {
      const response: CandidateListResponse = await fetchCandidates(toApiFilters(activeFilters));
      setCandidates(response.data ?? []);
      setError(null);
      setSuccessMessage("Filtros aplicados correctamente");
    } catch (unknownError: unknown) {
      const message = unknownError instanceof Error ? unknownError.message : "Error al obtener candidatos";
      setError(message);
      setCandidates([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const syncUrl = useCallback((nextFilters: FiltersState) => {
    const params = toSearchParams(nextFilters);
    const url = `${window.location.pathname}?${params.toString()}`;
    window.history.replaceState(null, "", url);
  }, []);

  const handleApply = () => {
    const nextFilters = { ...filters, search: filters.search.trim() };
    setFilters(nextFilters);
    syncUrl(nextFilters);
    void loadCandidates(nextFilters);
  };

  const handleClear = () => {
    setFilters(DEFAULT_FILTERS);
    syncUrl(DEFAULT_FILTERS);
    void loadCandidates(DEFAULT_FILTERS);
  };

  const handleCreate = async (payload: CandidatePayload) => {
    setIsCreating(true);
    setCreateError(null);
    setCreateSuccess(null);
    try {
      await createCandidate(payload);
      setCreateSuccess("Candidatura creada correctamente");
      setShowCreateForm(false);
      await loadCandidates(filters);
    } catch (unknownError: unknown) {
      const message =
        unknownError instanceof Error ? unknownError.message : "No se pudo crear la candidatura";
      setCreateError(message);
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <>
      <div className="mb-6 w-full rounded border border-zinc-200 p-4">
        <button
          type="button"
          onClick={() => {
            setShowCreateForm((prev) => !prev);
            setCreateError(null);
            setCreateSuccess(null);
          }}
          className="rounded bg-emerald-600 px-4 py-2 text-white"
        >
          {showCreateForm ? "Cerrar formulario" : "Nueva candidatura"}
        </button>

        {createSuccess && <p className="mt-2 text-green-700">{createSuccess}</p>}
        {createError && <p className="mt-2 text-red-600">{createError}</p>}

        {showCreateForm && (
          <div className="mt-4">
            <CandidateForm
              mode="create"
              isSubmitting={isCreating}
              submitLabel="Registrar candidatura"
              onSubmit={handleCreate}
              onCancel={() => setShowCreateForm(false)}
            />
          </div>
        )}
      </div>

      <CandidateFilters
        filters={filters}
        isLoading={isLoading}
        onChange={setFilters}
        onApply={handleApply}
        onClear={handleClear}
      />

      {isLoading && <div>Cargando candidatos...</div>}
      {!isLoading && successMessage && <div className="text-green-700">{successMessage}</div>}
      {!isLoading && error && <div className="text-red-500">{error}</div>}
      {!isLoading && !error && candidates.length === 0 && (
        <div>No hay candidatos para los filtros seleccionados.</div>
      )}
      {!isLoading && !error && candidates.length > 0 && <CandidatesTable candidates={candidates} />}
    </>
  );
}
