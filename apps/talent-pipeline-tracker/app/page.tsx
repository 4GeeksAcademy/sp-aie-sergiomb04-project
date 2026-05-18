
import { fetchCandidates } from "../services/api";
import React from "react";

type Candidate = {
  id: string;
  full_name: string;
  email: string;
  phone: string;
  position: string;
  status: string;
  stage: string;
};

export default async function Home() {
  let candidates: Candidate[] = [];
  let error = null;
  try {
    const data = await fetchCandidates();
    candidates = data.data || [];
  } catch (e: any) {
    error = e.message;
  }

  return (
    <div className="flex flex-col flex-1 items-center justify-center bg-zinc-50 font-sans dark:bg-black min-h-screen">
      <main className="flex flex-1 w-full max-w-3xl flex-col items-center justify-between py-16 px-4 bg-white dark:bg-black sm:items-start">
        <h1 className="text-3xl font-bold mb-8 text-black dark:text-zinc-50">Listado de Candidatos</h1>
        {error && <div className="text-red-500">{error}</div>}
        {!error && candidates.length === 0 && <div>No hay candidatos.</div>}
        {!error && candidates.length > 0 && (
          <table className="min-w-full border border-zinc-200 dark:border-zinc-700">
            <thead>
              <tr className="bg-zinc-100 dark:bg-zinc-800">
                <th className="px-4 py-2">Nombre</th>
                <th className="px-4 py-2">Puesto</th>
                <th className="px-4 py-2">Estado</th>
                <th className="px-4 py-2">Etapa</th>
              </tr>
            </thead>
            <tbody>
              {candidates.map((c) => (
                <tr key={c.id} className="border-t border-zinc-200 dark:border-zinc-700">
                  <td className="px-4 py-2">{c.full_name}</td>
                  <td className="px-4 py-2">{c.position}</td>
                  <td className="px-4 py-2">{c.status}</td>
                  <td className="px-4 py-2">{c.stage}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </main>
    </div>
  );
}
