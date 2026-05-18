import React from "react";
import Link from "next/link";
import { Candidate } from "@/app/components/candidates/types";
import { prettifyFilterValue } from "./utils";

type CandidatesTableProps = {
  candidates: Candidate[];
};

export function CandidatesTable({ candidates }: CandidatesTableProps) {
  return (
    <div className="w-full overflow-x-auto">
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
          {candidates.map((candidate) => (
            <tr key={candidate.id} className="border-t border-zinc-200 dark:border-zinc-700">
              <td className="px-4 py-2">
                <Link href={`/candidates/${candidate.id}`} className="text-blue-600 hover:underline">
                  {candidate.full_name}
                </Link>
              </td>
              <td className="px-4 py-2">{candidate.position}</td>
              <td className="px-4 py-2">{prettifyFilterValue(candidate.status)}</td>
              <td className="px-4 py-2">{prettifyFilterValue(candidate.stage)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
