"use client";

import React, { useState } from "react";
import { patchCandidateStatusAndStage, updateCandidate } from "@/services/api";
import { CandidateForm } from "./CandidateForm";
import { NotesSection } from "./NotesSection";
import { CandidateDetail as CandidateDetailType, CandidateNote, CandidatePayload } from "./types";
import { STAGE_OPTIONS, STATUS_OPTIONS, prettifyFilterValue } from "./utils";

type CandidateDetailProps = {
  candidate: CandidateDetailType;
  initialNotes?: CandidateNote[];
};

export function CandidateDetail({ candidate, initialNotes }: CandidateDetailProps) {
  const [candidateData, setCandidateData] = useState(candidate);
  const [status, setStatus] = useState(candidate.status);
  const [stage, setStage] = useState(candidate.stage);
  const [saving, setSaving] = useState(false);
  const [isUpdatingFullRecord, setIsUpdatingFullRecord] = useState(false);
  const [showEditForm, setShowEditForm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handlePatchStatusAndStage = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      const updated = await patchCandidateStatusAndStage(candidateData.id, { status, stage });
      setCandidateData(updated);
      setSuccess("Estado y etapa actualizados correctamente");
    } catch (unknownError: unknown) {
      setError(unknownError instanceof Error ? unknownError.message : "Error al actualizar");
    } finally {
      setSaving(false);
    }
  };

  const handleFullUpdate = async (payload: CandidatePayload) => {
    setIsUpdatingFullRecord(true);
    setError(null);
    setSuccess(null);

    try {
      const updated = await updateCandidate(candidateData.id, payload);
      setCandidateData(updated);
      setStatus(updated.status);
      setStage(updated.stage);
      setSuccess("Candidatura actualizada correctamente");
      setShowEditForm(false);
    } catch (unknownError: unknown) {
      setError(
        unknownError instanceof Error ? unknownError.message : "No se pudo actualizar la candidatura"
      );
    } finally {
      setIsUpdatingFullRecord(false);
    }
  };

  const initialEditValues: CandidatePayload = {
    full_name: candidateData.full_name,
    email: candidateData.email,
    phone: candidateData.phone,
    position: candidateData.position,
    linkedin_url: candidateData.linkedin_url,
    cv_url: candidateData.cv_url,
    status: candidateData.status,
    stage: candidateData.stage,
    experience_years: candidateData.experience_years,
  };

  return (
    <div className="max-w-2xl mx-auto mt-6 rounded bg-white p-6 shadow dark:bg-zinc-900">
      <div className="mb-4 flex items-center justify-between gap-2">
        <h1 className="text-2xl font-bold">{candidateData.full_name}</h1>
        <button
          type="button"
          onClick={() => {
            setShowEditForm((prev) => !prev);
            setError(null);
            setSuccess(null);
          }}
          className="rounded border border-zinc-300 px-3 py-1 text-sm"
        >
          {showEditForm ? "Cerrar edicion" : "Editar candidatura (PUT)"}
        </button>
      </div>

      {showEditForm && (
        <div className="mb-5">
          <CandidateForm
            mode="edit"
            initialValues={initialEditValues}
            isSubmitting={isUpdatingFullRecord}
            submitLabel="Guardar cambios"
            onSubmit={handleFullUpdate}
            onCancel={() => setShowEditForm(false)}
          />
        </div>
      )}

      <div className="mb-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <p><strong>Email:</strong> {candidateData.email}</p>
          <p><strong>Telefono:</strong> {candidateData.phone}</p>
          <p><strong>Puesto:</strong> {candidateData.position}</p>
          <p>
            <strong>LinkedIn:</strong>{" "}
            <a
              href={candidateData.linkedin_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:underline"
            >
              Perfil
            </a>
          </p>
          <p>
            <strong>CV:</strong>{" "}
            <a
              href={candidateData.cv_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:underline"
            >
              Descargar
            </a>
          </p>
        </div>

        <div>
          <form onSubmit={handlePatchStatusAndStage} className="space-y-2">
            <label className="block">
              <span className="mb-1 block text-sm font-semibold text-gray-200">
                Estado:
              </span>

              <select
                value={status}
                onChange={(event) =>
                  setStatus(event.target.value as CandidatePayload["status"])
                }
                disabled={saving}
                className="
      w-full rounded-lg border border-gray-600
      bg-gray-800 px-3 py-2
      text-white placeholder-gray-400
      shadow-sm outline-none
      transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500
      disabled:cursor-not-allowed disabled:opacity-50
    "
              >
                {STATUS_OPTIONS.map((option) => (
                  <option
                    key={option}
                    value={option}
                    className="bg-gray-800 text-white"
                  >
                    {prettifyFilterValue(option)}
                  </option>
                ))}
              </select>
            </label>

            <label className="block">
              <span className="mb-1 block text-sm font-semibold text-gray-200">
                Etapa:
              </span>

              <select
                value={stage}
                onChange={(event) =>
                  setStage(event.target.value as CandidatePayload["stage"])
                }
                disabled={saving}
                className="
      w-full rounded-lg border border-gray-600
      bg-gray-800 px-3 py-2
      text-white placeholder-gray-400
      shadow-sm outline-none
      transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500
      disabled:cursor-not-allowed disabled:opacity-50
    "
              >
                {STAGE_OPTIONS.map((option) => (
                  <option
                    key={option}
                    value={option}
                    className="bg-gray-800 text-white"
                  >
                    {prettifyFilterValue(option)}
                  </option>
                ))}
              </select>
            </label>

            <button
              type="submit"
              className="rounded bg-blue-600 px-4 py-1 text-white"
              disabled={saving}
            >
              {saving ? "Guardando..." : "Guardar"}
            </button>
          </form>

          {success && <p className="text-sm text-green-700">{success}</p>}
          {error && <p className="text-sm text-red-600">{error}</p>}

          <p><strong>Anios de experiencia:</strong> {candidateData.experience_years}</p>
          <p><strong>Notas:</strong> {candidateData.notes_count}</p>
          <p suppressHydrationWarning>
            <strong>Aplico el:</strong> {new Date(candidateData.applied_at).toLocaleDateString("es-ES")} {" "}
            {new Date(candidateData.applied_at).toLocaleTimeString("es-ES", {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </p>
          <p suppressHydrationWarning>
            <strong>Actualizado el:</strong> {new Date(candidateData.updated_at).toLocaleDateString("es-ES")} {" "}
            {new Date(candidateData.updated_at).toLocaleTimeString("es-ES", {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </p>
        </div>
      </div>

      <NotesSection recordId={candidateData.id} initialNotes={initialNotes} />
    </div>
  );
}
