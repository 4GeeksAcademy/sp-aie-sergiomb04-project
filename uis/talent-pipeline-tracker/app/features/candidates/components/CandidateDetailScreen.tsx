"use client";

import { useEffect, useState } from "react";

import { CandidateDetail } from "@/app/features/candidates/components/CandidateDetail";
import { getCandidateById, getCandidateNotes } from "@/app/features/candidates/services/candidates-api";
import { CandidateDetail as CandidateDetailType, CandidateNote } from "@/app/features/candidates/types/candidate";

type CandidateDetailScreenProps = {
  id: string;
};

export function CandidateDetailScreen({ id }: CandidateDetailScreenProps) {
  const [candidate, setCandidate] = useState<CandidateDetailType | null>(null);
  const [notes, setNotes] = useState<CandidateNote[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadCandidate = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const [candidateData, notesResponse] = await Promise.all([
          getCandidateById(id),
          getCandidateNotes(id),
        ]);

        setCandidate(candidateData);
        setNotes(notesResponse.data ?? []);
      } catch (unknownError: unknown) {
        setError(
          unknownError instanceof Error
            ? unknownError.message
            : "No se pudo cargar la candidatura"
        );
      } finally {
        setIsLoading(false);
      }
    };

    void loadCandidate();
  }, [id]);

  if (isLoading) {
    return (
      <main className="min-h-screen bg-zinc-50 p-6">
        <p className="text-sm text-zinc-700">Cargando candidatura...</p>
      </main>
    );
  }

  if (error || !candidate) {
    return (
      <main className="min-h-screen bg-zinc-50 p-6">
        <p className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error ?? "No se encontró la candidatura"}
        </p>
      </main>
    );
  }

  return <CandidateDetail candidate={candidate} initialNotes={notes} />;
}
