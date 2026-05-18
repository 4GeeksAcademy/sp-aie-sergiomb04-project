"use client";

import React, { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { fetchCandidates } from "../../../services/api";
import { CandidateFilters } from "./CandidateFilters";
import { CandidatesTable } from "@/app/components/candidates/CandidatesTable";
import { Candidate, CandidateListResponse } from "./types";
import { DEFAULT_FILTERS, FiltersState } from "./utils";

function toApiFilters(filters: FiltersState) {
  return {
    status: filters.status || undefined,
    stage: filters.stage || undefined,
    search: filters.search.trim() || undefined,
    page: filters.page,
    limit: filters.limit,
  };
}

function fromSearchParams(params: URLSearchParams): FiltersState {
  return {
    status: params.get("status") || "",
    stage: params.get("stage") || "",
    search: params.get("search") || "",
    page: parseInt(params.get("page") || "1", 10),
    limit: parseInt(params.get("limit") || "20", 10),
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
};

export function CandidatesDashboard({
  initialCandidates,
  initialError,
}: CandidatesDashboardProps) {
  const searchParams = useSearchParams();
  const [filters, setFilters] = useState<FiltersState>(() => fromSearchParams(searchParams));
  const [candidates, setCandidates] = useState<Candidate[]>(initialCandidates);
  const [error, setError] = useState<string | null>(initialError);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const loadCandidates = useCallback(async (activeFilters: FiltersState) => {
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

  useEffect(() => {
    const params = toSearchParams(filters);
    const url = `${window.location.pathname}?${params.toString()}`;
    window.history.replaceState(null, "", url);
  }, [filters]);

  useEffect(() => {
    void loadCandidates(filters);
  }, [filters, loadCandidates]);

  const handleApply = async () => {
    const nextFilters = { ...filters, search: filters.search.trim() };
    setFilters(nextFilters);
    setIsLoading(true);
  };

  const handleClear = async () => {
    setFilters(DEFAULT_FILTERS);
    setIsLoading(true);
  };

  return (
    <>
      <CandidateFilters
        filters={filters}
        isLoading={isLoading}
        onChange={setFilters}
        onApply={() => {
          void handleApply();
        }}
        onClear={() => {
          void handleClear();
        }}
      />

      {isLoading && <div>Cargando candidatos...</div>}
      {!isLoading && error && <div className="text-red-500">{error}</div>}
      {!isLoading && !error && candidates.length === 0 && (
        <div>No hay candidatos para los filtros seleccionados.</div>
      )}
      {!isLoading && !error && candidates.length > 0 && <CandidatesTable candidates={candidates} />}
    </>
  );
}
