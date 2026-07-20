import { IncidentUploadPanel } from "@/app/features/incidents/components/IncidentUploadPanel";

export default function IncidentsPage() {
  return (
    <main className="flex flex-1 flex-col gap-8 px-6 py-10 lg:px-10">
      <IncidentUploadPanel />
    </main>
  );
}