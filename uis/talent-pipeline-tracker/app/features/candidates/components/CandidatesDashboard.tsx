"use client";

import Link from "next/link";
import React from "react";
import { CandidateFilters } from "./CandidateFilters";
import { CandidatesTable } from "./CandidatesTable";
import { Candidate, CandidateFilters as CandidateFiltersType } from "@/app/features/candidates/types/candidate";
import { CandidateForm } from "./CandidateForm";
import { useCandidatesDashboard } from "@/app/features/candidates/hooks/useCandidatesDashboard";
import { useAuthSession } from "@/app/features/auth/components/AuthSessionProvider";

type CandidatesDashboardProps = {
  initialCandidates: Candidate[];
  initialError: string | null;
  initialFilters: CandidateFiltersType;
};

export function CandidatesDashboard({
  initialCandidates,
  initialError,
  initialFilters,
}: CandidatesDashboardProps) {
  const { user, logout } = useAuthSession();

  const {
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
  } = useCandidatesDashboard({
    initialCandidates,
    initialError,
    initialFilters,
  });

  return (
    <>
      <div className="mb-4 flex w-full items-center justify-between rounded border border-zinc-200 bg-zinc-50 p-3">
        <div>
          <p className="text-sm font-semibold text-zinc-800">{user?.email ?? "Usuario"}</p>
          <p className="text-xs text-zinc-600">Sesión autenticada</p>
        </div>

        <div className="flex items-center gap-3">
          <Link href="/account/profile" className="text-sm text-blue-700 hover:underline">
            Mi perfil
          </Link>
          <button
            type="button"
            onClick={logout}
            className="rounded border border-zinc-300 px-3 py-1 text-sm"
          >
            Cerrar sesión
          </button>
        </div>
      </div>

      <div className="mb-6 w-full rounded border border-zinc-200 p-4">
        <button
          type="button"
          onClick={handleToggleCreateForm}
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
      {!isLoading && error && <div className="text-red-500">{error}</div>}
      {!isLoading && !error && candidates.length === 0 && (
        <div>No hay candidatos para los filtros seleccionados.</div>
      )}
      {!isLoading && !error && candidates.length > 0 && <CandidatesTable candidates={candidates} />}
    </>
  );
}
