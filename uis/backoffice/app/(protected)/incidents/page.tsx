import dynamic from "next/dynamic";

import { IncidentList } from "@/app/features/incidents/components/IncidentList";
import { IncidentRegistrationForm } from "@/app/features/incidents/components/IncidentRegistrationForm";

const IncidentUploadPanel = dynamic(
  () => import("@/app/features/incidents/components/IncidentUploadPanel").then((mod) => mod.IncidentUploadPanel),
  {
    loading: () => (
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-sm text-slate-500">Cargando módulo de análisis CSV...</p>
      </section>
    ),
  }
);

const IncidentSummaryPanel = dynamic(
  () => import("@/app/features/incidents/components/IncidentSummaryPanel").then((mod) => mod.IncidentSummaryPanel),
  {
    loading: () => (
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-sm text-slate-500">Cargando resumen de incidencias...</p>
      </section>
    ),
  }
);

export default function IncidentsPage() {
  return (
    <main className="flex flex-1 flex-col gap-8 px-6 py-10 lg:px-10">
      <IncidentUploadPanel />
      <IncidentRegistrationForm />
      <IncidentList />
      <IncidentSummaryPanel />
    </main>
  );
}