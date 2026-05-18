"use client";
import React, { useCallback, useState } from "react";
import { addCandidateNote, deleteCandidateNote, getCandidateNotes } from "@/services/api";
import { CandidateNote } from "./types";

interface NotesSectionProps {
  recordId: string;
  initialNotes?: CandidateNote[];
}

export const NotesSection: React.FC<NotesSectionProps> = ({ recordId, initialNotes = [] }) => {
  const [notes, setNotes] = useState<CandidateNote[]>(initialNotes);
  const [newNote, setNewNote] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const deleteInFlightRef = React.useRef(false);

  const fetchNotes = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getCandidateNotes(recordId);
      setNotes(response.data || []);
    } catch (unknownError: unknown) {
      setError(unknownError instanceof Error ? unknownError.message : "Error al cargar notas");
    } finally {
      setLoading(false);
    }
  }, [recordId]);

  const handleAddNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (loading) return;
    if (!newNote.trim()) return;
    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      await addCandidateNote(recordId, newNote.trim());
      setNewNote("");
      setSuccess("Nota agregada correctamente");
      await fetchNotes();
    } catch (unknownError: unknown) {
      setError(unknownError instanceof Error ? unknownError.message : "No se pudo agregar la nota");
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteNote = async (noteId: string) => {
    if (loading || deleteInFlightRef.current) return;
    deleteInFlightRef.current = true;
    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      await deleteCandidateNote(recordId, noteId);
      setNotes((prevNotes) => prevNotes.filter((note) => note.id !== noteId));
      setSuccess("Nota eliminada correctamente");
    } catch (unknownError: unknown) {
      setError(unknownError instanceof Error ? unknownError.message : "No se pudo eliminar la nota");
    } finally {
      deleteInFlightRef.current = false;
      setLoading(false);
    }
  };

  return (
    <section className="my-8 rounded-2xl border border-zinc-200 bg-white shadow-sm p-5 dark:bg-zinc-900 dark:border-zinc-700">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-zinc-800 dark:text-zinc-100">
          Notas
        </h2>

        <span className="text-sm text-zinc-500 dark:text-zinc-400">
          {notes.length} notas
        </span>
      </div>

      <form onSubmit={handleAddNote} className="flex gap-2 mb-5">
        <input
          type="text"
          value={newNote}
          onChange={(e) => setNewNote(e.target.value)}
          placeholder="Escribe una nota..."
          disabled={loading}
          className="
          flex-1
          rounded-xl
          border
          border-zinc-300
          bg-zinc-50
          px-4
          py-2
          text-zinc-800
          placeholder:text-zinc-400
          focus:outline-none
          focus:ring-2
          focus:ring-blue-500
          focus:border-blue-500
          dark:bg-zinc-800
          dark:border-zinc-600
          dark:text-zinc-100
        "
        />

        <button
          type="submit"
          disabled={loading}
          className="
          rounded-xl
          bg-blue-600
          hover:bg-blue-700
          transition-colors
          px-5
          py-2
          text-white
          font-medium
          disabled:opacity-50
        "
        >
          Añadir
        </button>
      </form>

      {loading && (
        <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-3">
          Cargando...
        </p>
      )}

      {success && (
        <p className="mb-3 rounded-lg bg-green-100 text-green-700 px-3 py-2 text-sm dark:bg-green-900/30 dark:text-green-400">
          {success}
        </p>
      )}

      {error && (
        <p className="mb-3 rounded-lg bg-red-100 text-red-700 px-3 py-2 text-sm dark:bg-red-900/30 dark:text-red-400">
          {error}
        </p>
      )}

      <ul className="space-y-3">
        {notes.map((note) => (
          <li
            key={note.id}
            className="
            flex
            items-start
            justify-between
            gap-4
            rounded-xl
            border
            border-zinc-200
            bg-zinc-50
            p-4
            dark:bg-zinc-800/70
            dark:border-zinc-700
          "
          >
            <div className="flex-1">
              <p className="text-zinc-800 dark:text-zinc-100">
                {note.content}
              </p>

              <span
                suppressHydrationWarning
                className="mt-1 block text-xs text-zinc-500 dark:text-zinc-400"
              >
                {new Date(note.created_at).toLocaleString("es-ES", { timeZone: "Europe/Madrid" })}
              </span>
            </div>

            <button
              type="button"
              onClick={() => handleDeleteNote(note.id)}
              disabled={loading}
              className="
              text-sm
              font-medium
              text-red-600
              hover:text-red-700
              hover:underline
              transition-colors
              disabled:opacity-50
            "
            >
              Eliminar
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
};
