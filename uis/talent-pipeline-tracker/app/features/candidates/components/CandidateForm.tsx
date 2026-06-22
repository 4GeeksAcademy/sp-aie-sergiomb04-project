"use client";

import React, { useState } from "react";
import { CandidatePayload } from "@/app/features/candidates/types/candidate";
import { STAGE_OPTIONS, STATUS_OPTIONS, prettifyFilterValue } from "@/app/features/candidates/lib/candidate-filters";

type CandidateFormProps = {
  mode: "create" | "edit";
  initialValues?: CandidatePayload;
  isSubmitting: boolean;
  submitLabel: string;
  onSubmit: (payload: CandidatePayload) => Promise<void>;
  onCancel?: () => void;
};

const DEFAULT_PAYLOAD: CandidatePayload = {
  full_name: "",
  email: "",
  phone: "",
  position: "",
  linkedin_url: "",
  cv_url: "",
  status: "received",
  stage: "pending",
  experience_years: 0,
};

export function CandidateForm({
  mode,
  initialValues,
  isSubmitting,
  submitLabel,
  onSubmit,
  onCancel,
}: CandidateFormProps) {
  const [form, setForm] = useState<CandidatePayload>(initialValues ?? DEFAULT_PAYLOAD);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    await onSubmit({
      ...form,
      full_name: form.full_name.trim(),
      email: form.email.trim(),
      phone: form.phone.trim(),
      position: form.position.trim(),
      linkedin_url: form.linkedin_url.trim(),
      cv_url: form.cv_url.trim(),
      experience_years: Number(form.experience_years),
    });
  };

  return (
    <form onSubmit={handleSubmit} className="w-full space-y-3 rounded border border-zinc-200 p-4">
      <h2 className="text-lg font-semibold">
        {mode === "create" ? "Registrar nueva candidatura" : "Editar candidatura"}
      </h2>

      <input
        required
        value={form.full_name}
        onChange={(event) => setForm({ ...form, full_name: event.target.value })}
        placeholder="Nombre completo"
        className="w-full rounded border border-zinc-300 px-3 py-2"
      />
      <input
        required
        type="email"
        value={form.email}
        onChange={(event) => setForm({ ...form, email: event.target.value })}
        placeholder="Email"
        className="w-full rounded border border-zinc-300 px-3 py-2"
      />
      <input
        required
        value={form.phone}
        onChange={(event) => setForm({ ...form, phone: event.target.value })}
        placeholder="Telefono"
        className="w-full rounded border border-zinc-300 px-3 py-2"
      />
      <input
        required
        value={form.position}
        onChange={(event) => setForm({ ...form, position: event.target.value })}
        placeholder="Puesto"
        className="w-full rounded border border-zinc-300 px-3 py-2"
      />
      <input
        required
        type="url"
        value={form.linkedin_url}
        onChange={(event) => setForm({ ...form, linkedin_url: event.target.value })}
        placeholder="URL LinkedIn"
        className="w-full rounded border border-zinc-300 px-3 py-2"
      />
      <input
        required
        type="url"
        value={form.cv_url}
        onChange={(event) => setForm({ ...form, cv_url: event.target.value })}
        placeholder="URL CV"
        className="w-full rounded border border-zinc-300 px-3 py-2"
      />

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <select
          value={form.status}
          onChange={(event) =>
            setForm({ ...form, status: event.target.value as CandidatePayload["status"] })
          }
          className="rounded border border-zinc-300 px-3 py-2"
        >
          {STATUS_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {prettifyFilterValue(option)}
            </option>
          ))}
        </select>

        <select
          value={form.stage}
          onChange={(event) =>
            setForm({ ...form, stage: event.target.value as CandidatePayload["stage"] })
          }
          className="rounded border border-zinc-300 px-3 py-2"
        >
          {STAGE_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {prettifyFilterValue(option)}
            </option>
          ))}
        </select>

        <input
          required
          min={0}
          type="number"
          value={form.experience_years}
          onChange={(event) =>
            setForm({ ...form, experience_years: Number.parseInt(event.target.value || "0", 10) })
          }
          placeholder="Anios exp."
          className="rounded border border-zinc-300 px-3 py-2"
        />
      </div>

      <div className="flex gap-2">
        <button
          type="submit"
          disabled={isSubmitting}
          className="rounded bg-blue-600 px-4 py-2 text-white disabled:opacity-60"
        >
          {isSubmitting ? "Guardando..." : submitLabel}
        </button>
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            disabled={isSubmitting}
            className="rounded border border-zinc-300 px-4 py-2"
          >
            Cancelar
          </button>
        )}
      </div>
    </form>
  );
}
