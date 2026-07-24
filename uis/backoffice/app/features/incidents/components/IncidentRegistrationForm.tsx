"use client";

import React, { useCallback, useState } from "react";

import { createIncident } from "@/app/features/incidents/services/incident-api";
import {
  BRANCH_LABELS,
  CATEGORY_LABELS,
  INCIDENT_BRANCHES,
  INCIDENT_CATEGORIES,
  INCIDENT_ORIGINS,
  ORIGIN_LABELS,
} from "@/app/features/incidents/types/incident-domain";
import type {
  IncidentBranch,
  IncidentCategory,
  IncidentCreateInput,
  IncidentOrigin,
} from "@/app/features/incidents/types/incident-domain";

type FieldErrors = Partial<Record<keyof IncidentCreateInput, string>>;

const INITIAL_STATE: IncidentCreateInput = {
  title: "",
  description: "",
  category: "" as IncidentCategory,
  origin: "customer",
  branch: "" as IncidentBranch,
};

export function IncidentRegistrationForm() {
  const [form, setForm] = useState<IncidentCreateInput>({ ...INITIAL_STATE });
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [globalError, setGlobalError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);

  const updateField = useCallback(
    <K extends keyof IncidentCreateInput>(
      field: K,
      value: IncidentCreateInput[K],
    ) => {
      setForm((prev) => ({ ...prev, [field]: value }));
      setFieldErrors((prev) => ({ ...prev, [field]: undefined }));
      setGlobalError(null);
      setSuccess(null);
    },
    [],
  );

  const validate = useCallback((): boolean => {
    const errors: FieldErrors = {};
    if (!form.title.trim()) errors.title = "El título es obligatorio";
    if (!form.description.trim()) errors.description = "La descripción es obligatoria";
    if (!form.category) errors.category = "Selecciona una categoría";
    if (!form.branch) errors.branch = "Selecciona una sede";
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  }, [form]);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!validate()) return;

      setIsSubmitting(true);
      setGlobalError(null);
      setSuccess(null);

      try {
        await createIncident(form);
        setForm({ ...INITIAL_STATE });
        setSuccess("Incidencia registrada correctamente");
      } catch (err: unknown) {
        const message =
          err instanceof Error ? err.message : "Error al registrar la incidencia";
        setGlobalError(message);
      } finally {
        setIsSubmitting(false);
      }
    },
    [form, validate],
  );

  const isBranchHighlighted = form.origin === "branch";

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-xl font-semibold text-slate-950">Registrar incidencia</h2>
      <p className="mt-1 text-sm text-slate-600">
        Introduce los datos de la nueva incidencia. Todos los campos marcados con * son
        obligatorios.
      </p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-5">
        {/* Title */}
        <div>
          <label htmlFor="incident-title" className="block text-sm font-medium text-slate-700">
            Título *
          </label>
          <input
            id="incident-title"
            type="text"
            value={form.title}
            onChange={(e) => updateField("title", e.target.value)}
            className="mt-1 block w-full rounded-xl border border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500"
            placeholder="Ej: Paquete no entregado"
          />
          {fieldErrors.title && (
            <p className="mt-1 text-sm text-rose-600">{fieldErrors.title}</p>
          )}
        </div>

        {/* Description */}
        <div>
          <label htmlFor="incident-description" className="block text-sm font-medium text-slate-700">
            Descripción *
          </label>
          <textarea
            id="incident-description"
            rows={3}
            value={form.description}
            onChange={(e) => updateField("description", e.target.value)}
            className="mt-1 block w-full rounded-xl border border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500"
            placeholder="Describe la incidencia con detalle"
          />
          {fieldErrors.description && (
            <p className="mt-1 text-sm text-rose-600">{fieldErrors.description}</p>
          )}
        </div>

        {/* Category */}
        <div>
          <label htmlFor="incident-category" className="block text-sm font-medium text-slate-700">
            Categoría *
          </label>
          <select
            id="incident-category"
            value={form.category}
            onChange={(e) => updateField("category", e.target.value as IncidentCategory)}
            className="mt-1 block w-full rounded-xl border border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-900 focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500"
          >
            <option value="">Selecciona una categoría</option>
            {INCIDENT_CATEGORIES.map((cat) => (
              <option key={cat} value={cat}>
                {CATEGORY_LABELS[cat]}
              </option>
            ))}
          </select>
          {fieldErrors.category && (
            <p className="mt-1 text-sm text-rose-600">{fieldErrors.category}</p>
          )}
        </div>

        {/* Origin */}
        <div>
          <label htmlFor="incident-origin" className="block text-sm font-medium text-slate-700">
            Origen *
          </label>
          <select
            id="incident-origin"
            value={form.origin}
            onChange={(e) => updateField("origin", e.target.value as IncidentOrigin)}
            className="mt-1 block w-full rounded-xl border border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-900 focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500"
          >
            {INCIDENT_ORIGINS.map((origin) => (
              <option key={origin} value={origin}>
                {ORIGIN_LABELS[origin]}
              </option>
            ))}
          </select>
        </div>

        {/* Branch */}
        <div
          className={`rounded-xl border p-4 transition-colors ${
            isBranchHighlighted
              ? "border-amber-300 bg-amber-50"
              : "border-transparent bg-transparent"
          }`}
        >
          <label htmlFor="incident-branch" className="block text-sm font-medium text-slate-700">
            Sede *
            {isBranchHighlighted && (
              <span className="ml-2 text-xs font-normal text-amber-700">
                (resaltado porque el origen es &quot;sede&quot;)
              </span>
            )}
          </label>
          <select
            id="incident-branch"
            value={form.branch}
            onChange={(e) => updateField("branch", e.target.value as IncidentBranch)}
            className="mt-1 block w-full rounded-xl border border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-900 focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500"
          >
            <option value="">Selecciona una sede</option>
            {INCIDENT_BRANCHES.map((branch) => (
              <option key={branch} value={branch}>
                {BRANCH_LABELS[branch]}
              </option>
            ))}
          </select>
          {fieldErrors.branch && (
            <p className="mt-1 text-sm text-rose-600">{fieldErrors.branch}</p>
          )}
        </div>

        {/* Global error */}
        {globalError && (
          <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {globalError}
          </div>
        )}

        {/* Success */}
        {success && (
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
            {success}
          </div>
        )}

        {/* Submit */}
        <button
          type="submit"
          disabled={isSubmitting}
          className="rounded-xl bg-slate-900 px-6 py-2.5 text-sm font-semibold text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isSubmitting ? "Guardando..." : "Registrar incidencia"}
        </button>
      </form>
    </section>
  );
}