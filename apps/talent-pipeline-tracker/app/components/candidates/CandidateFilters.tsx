"use client";

import React from "react";
import { FiltersState, STAGE_OPTIONS, STATUS_OPTIONS, prettifyFilterValue } from "./utils";

type CandidateFiltersProps = {
  filters: FiltersState;
  isLoading: boolean;
  onChange: (next: FiltersState) => void;
  onApply: () => void;
  onClear: () => void;
};

function clampPage(value: number): number {
  if (Number.isNaN(value) || value < 1) return 1;
  return value;
}

function clampLimit(value: number): number {
  if (Number.isNaN(value) || value < 1) return 20;
  if (value > 100) return 100;
  return value;
}

export function CandidateFilters({
  filters,
  isLoading,
  onChange,
  onApply,
  onClear,
}: CandidateFiltersProps) {
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        onApply();
      }}
      className="w-full mb-6 grid grid-cols-1 gap-3 sm:grid-cols-2"
    >
      <select
        name="status"
        value={filters.status}
        onChange={(event) => onChange({ ...filters, status: event.target.value, page: 1 })}
        className="rounded border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
      >
        <option value="">Todos los estados</option>
        {STATUS_OPTIONS.map((option) => (
          <option key={option} value={option}>
            {prettifyFilterValue(option)}
          </option>
        ))}
      </select>

      <select
        name="stage"
        value={filters.stage}
        onChange={(event) => onChange({ ...filters, stage: event.target.value, page: 1 })}
        className="rounded border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
      >
        <option value="">Todas las etapas</option>
        {STAGE_OPTIONS.map((option) => (
          <option key={option} value={option}>
            {prettifyFilterValue(option)}
          </option>
        ))}
      </select>

      <input
        type="text"
        name="search"
        value={filters.search}
        onChange={(event) => onChange({ ...filters, search: event.target.value, page: 1 })}
        placeholder="Buscar por nombre o email"
        className="rounded border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
      />

      <div className="grid grid-cols-2 gap-3">
        <input
          type="number"
          name="page"
          min={1}
          value={filters.page}
          onChange={(event) =>
            onChange({ ...filters, page: clampPage(Number.parseInt(event.target.value, 10)) })
          }
          className="rounded border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
        />
        <select
          name="limit"
          value={String(filters.limit)}
          onChange={(event) =>
            onChange({
              ...filters,
              limit: clampLimit(Number.parseInt(event.target.value, 10)),
              page: 1,
            })
          }
          className="rounded border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
        >
          {[10, 20, 50, 100].map((option) => (
            <option key={option} value={option}>
              {option} por pagina
            </option>
          ))}
        </select>
      </div>

      <div className="sm:col-span-2 flex gap-3">
        <button
          type="submit"
          disabled={isLoading}
          className="rounded bg-black px-4 py-2 text-sm font-medium text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-black"
        >
          {isLoading ? "Aplicando..." : "Aplicar filtros"}
        </button>
        <button
          type="button"
          onClick={onClear}
          disabled={isLoading}
          className="rounded border border-zinc-300 px-4 py-2 text-sm font-medium disabled:opacity-60 dark:border-zinc-700"
        >
          Limpiar
        </button>
      </div>
    </form>
  );
}
