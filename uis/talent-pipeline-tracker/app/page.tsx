
import { fetchCandidates } from "@/app/features/candidates/services/candidates-api";
import { CandidatesDashboard } from "@/app/features/candidates/components/CandidatesDashboard";
import { Candidate, CandidateFilters } from "@/app/features/candidates/types/candidate";
import Link from "next/link";
import React from "react";

type HomePageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

function parsePositiveInt(value: string | string[] | undefined, fallback: number): number {
  const source = Array.isArray(value) ? value[0] : value;
  const parsed = Number.parseInt(source ?? "", 10);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback;
}

export default async function Home({ searchParams }: HomePageProps) {
  const resolvedSearchParams = await searchParams;

  const initialFilters: CandidateFilters = {
    status: typeof resolvedSearchParams.status === "string" ? resolvedSearchParams.status : undefined,
    stage: typeof resolvedSearchParams.stage === "string" ? resolvedSearchParams.stage : undefined,
    search: typeof resolvedSearchParams.search === "string" ? resolvedSearchParams.search : undefined,
    page: parsePositiveInt(resolvedSearchParams.page, 1),
    limit: parsePositiveInt(resolvedSearchParams.limit, 20),
  };

  let initialCandidates: Candidate[] = [];
  let initialError: string | null = null;

  try {
    const response = await fetchCandidates(initialFilters);
    initialCandidates = response.data ?? [];
  } catch (unknownError: unknown) {
    initialError =
      unknownError instanceof Error ? unknownError.message : "Error al obtener candidatos";
  }

  return (
    <div className="flex flex-col flex-1 items-center justify-center bg-zinc-50 font-sans dark:bg-black min-h-screen">
      <main className="flex flex-1 w-full max-w-3xl flex-col items-center py-16 px-4 bg-white dark:bg-black sm:items-start">
        <div className="mb-8 flex w-full items-center justify-between gap-3">
          <h1 className="text-3xl font-bold text-black dark:text-zinc-50">Listado de Candidatos</h1>
          <Link
            href="/incidents"
            className="rounded-lg border border-zinc-300 px-3 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-100"
          >
            Ir a Incidents Analysis
          </Link>
        </div>
        <CandidatesDashboard
          initialCandidates={initialCandidates}
          initialError={initialError}
          initialFilters={initialFilters}
        />
      </main>
    </div>
  );
}
