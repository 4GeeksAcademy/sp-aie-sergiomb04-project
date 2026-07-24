"use client";

import { useCallback, useEffect, useState } from "react";
import { createCandidate, fetchCandidates } from "@/app/features/candidates/services/candidates-api";
import {
  Candidate,
  CandidateFilters,
  CandidateListResponse,
  CandidatePayload,
} from "@/app/features/candidates/types/candidate";
import { DEFAULT_FILTERS, FiltersState } from "@/app/features/candidates/lib/candidate-filters";

type UseCandidatesDashboardParams = {
  initialCandidates: Candidate[];
  initialError: string | null;
  initialFilters: CandidateFilters;
};

function normalizeFilters(filters: CandidateFilters): FiltersState {
  return {
    status: filters.status || "",
    stage: filters.stage || "",
    search: filters.search || "",
    page: filters.page || 1,
    limit: filters.limit || 20,
  };
}

function toApiFilters(filters: FiltersState): CandidateFilters {
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

export function useCandidatesDashboard({
  initialCandidates,
  initialError,
  initialFilters,
}: UseCandidatesDashboardParams) {
  const [filters, setFilters] = useState<FiltersState>(() => normalizeFilters(initialFilters));
  const [candidates, setCandidates] = useState<Candidate[]>(initialCandidates);
  const [error, setError] = useState<string | null>(initialError);
  const [isLoading, setIsLoading] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [createSuccess, setCreateSuccess] = useState<string | null>(null);

  const loadCandidates = useCallback(async (activeFilters: FiltersState) => {
    setIsLoading(true);
    try {
      const response: CandidateListResponse = await fetchCandidates(toApiFilters(activeFilters));
      setCandidates(response.data ?? []);
      setError(null);
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

  const handleToggleCreateForm = () => {
    setShowCreateForm((prev) => !prev);
    setCreateError(null);
    setCreateSuccess(null);
  };

  useEffect(() => {
    if (initialCandidates.length === 0 && !initialError) {
      void loadCandidates(normalizeFilters(initialFilters));
    }
  }, [initialCandidates.length, initialError, initialFilters, loadCandidates]);

  return {
    filters,
    setFilters,
    candidates,
    error,
    isLoading,
    showCreateForm,
    setShowCreateForm,
    isCreating,
    createError,
    createSuccess,
    handleApply,
    handleClear,
    handleCreate,
    handleToggleCreateForm,
  };
}
