"use client";

import React, { useCallback, useState } from "react";
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

type CandidatesDashboardProps = {
  initialCandidates: Candidate[];
  initialError: string | null;
};

export function CandidatesDashboard({
  initialCandidates,
  initialError,
}: CandidatesDashboardProps) {
  const [filters, setFilters] = useState<FiltersState>(DEFAULT_FILTERS);
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

  const handleApply = async () => {
    const nextFilters = { ...filters, search: filters.search.trim() };
    setFilters(nextFilters);
    setIsLoading(true);
    await loadCandidates(nextFilters);
  };

  const handleClear = async () => {
    setFilters(DEFAULT_FILTERS);
    setIsLoading(true);
    await loadCandidates(DEFAULT_FILTERS);
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
