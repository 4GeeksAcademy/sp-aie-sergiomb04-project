import { CandidatesDashboard } from "@/app/features/candidates/components/CandidatesDashboard";
import { CandidateFilters } from "@/app/features/candidates/types/candidate";
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

  return (
    <div className="flex flex-col flex-1 items-center justify-center bg-zinc-50 font-sans dark:bg-black min-h-screen">
      <main className="flex flex-1 w-full max-w-3xl flex-col items-center py-16 px-4 bg-white dark:bg-black sm:items-start">
        <h1 className="text-3xl font-bold mb-8 text-black dark:text-zinc-50">Listado de Candidatos</h1>
        <CandidatesDashboard
          initialCandidates={[]}
          initialError={null}
          initialFilters={initialFilters}
        />
      </main>
    </div>
  );
}
