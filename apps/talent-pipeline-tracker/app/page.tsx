
import { fetchCandidates } from "@/services/api";
import { CandidatesDashboard } from "@/app/components/candidates/CandidatesDashboard";
import { Candidate } from "@/app/components/candidates/types";
import React from "react";

export default async function Home() {
  let initialCandidates: Candidate[] = [];
  let initialError: string | null = null;

  try {
    const response = await fetchCandidates({ page: 1, limit: 20 });
    initialCandidates = response.data ?? [];
  } catch (unknownError: unknown) {
    initialError =
      unknownError instanceof Error ? unknownError.message : "Error al obtener candidatos";
  }

  return (
    <div className="flex flex-col flex-1 items-center justify-center bg-zinc-50 font-sans dark:bg-black min-h-screen">
      <main className="flex flex-1 w-full max-w-3xl flex-col items-center py-16 px-4 bg-white dark:bg-black sm:items-start">
        <h1 className="text-3xl font-bold mb-8 text-black dark:text-zinc-50">Listado de Candidatos</h1>
        <CandidatesDashboard initialCandidates={initialCandidates} initialError={initialError} />
      </main>
    </div>
  );
}
